from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from datetime import datetime
import functools
import concurrent.futures
import os
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)

class IndexStatus:
    """Singleton class to store the project index status."""
    _instance = None
    is_building: bool = False
    is_valid: bool = False
    structure: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

@functools.lru_cache(maxsize=32)
def get_project_structure(base_path: Path) -> Dict[str, Any]:
    """
    Build the project structure tree, respecting .gitignore rules.

    Args:
        base_path: The root directory to scan.

    Returns:
        A dictionary representing the project structure.
    """
    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    context_ignore_spec = parse_contextignore(base_path)

    def build_tree(path: Path, root: Path, is_dir_cached: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        if is_dir_cached is None:
            is_dir_cached = path.is_dir()

        entry = {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "name": path.name,
            "type": "directory" if is_dir_cached else "file",
            "children": []
        }

        if is_dir_cached:
            try:
                # Store children as tuples: (path_str, name, is_dir_bool)
                # This avoids keeping DirEntry objects (which can be problematic after iterator close)
                # and avoids extra stat calls by using cached is_dir result.
                children_data: List[Tuple[str, str, bool]] = []
                with os.scandir(path) as it:
                    for scandir_entry in it:
                        is_entry_dir = scandir_entry.is_dir()
                        if should_ignore(scandir_entry.path, base_path, git_root, ignore_spec, context_ignore_spec, is_dir=is_entry_dir):
                            continue
                        children_data.append((scandir_entry.path, scandir_entry.name, is_entry_dir))

                # Sort directories first, then files, both alphabetically
                children_data.sort(key=lambda x: (not x[2], x[1].lower()))

                for path_str, name, is_entry_dir in children_data:
                    child_path = Path(path_str)
                    child_entry = build_tree(child_path, root, is_dir_cached=is_entry_dir)
                    if child_entry:
                        entry["children"].append(child_entry)
            except (PermissionError, OSError):
                pass

        return entry

    root_entry = {
        "path": "",
        "name": base_path.name,
        "type": "directory",
        "children": []
    }

    try:
        children_data: List[Tuple[str, str, bool]] = []
        with os.scandir(base_path) as it:
            for scandir_entry in it:
                is_entry_dir = scandir_entry.is_dir()
                if should_ignore(scandir_entry.path, base_path, git_root, ignore_spec, context_ignore_spec, is_dir=is_entry_dir):
                    continue
                children_data.append((scandir_entry.path, scandir_entry.name, is_entry_dir))

        # Sort directories first, then files, both alphabetically
        children_data.sort(key=lambda x: (not x[2], x[1].lower()))

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Submit tasks passing the cached is_dir value to avoid initial stat in build_tree
            futures = {executor.submit(build_tree, Path(path_str), base_path, is_dir_cached=is_dir): (path_str, name, is_dir) for path_str, name, is_dir in children_data}
            for future in concurrent.futures.as_completed(futures):
                try:
                    child_entry = future.result()
                    if child_entry:
                        root_entry["children"].append(child_entry)
                except Exception:
                    continue

            # Sort the root children again because ThreadPoolExecutor completion order is non-deterministic
            root_entry["children"].sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
    except (PermissionError, OSError):
        pass

    return root_entry

async def build_and_save_index(base_path: Path) -> None:
    """
    Build and store the project structure in memory.

    Args:
        base_path: The root directory to scan.
    """
    index_status = IndexStatus()
    try:
        structure = await run_in_threadpool(get_project_structure, base_path)
        index_status.structure = structure
        index_status.created_at = datetime.now()
        index_status.is_valid = True
    finally:
        index_status.is_building = False

async def get_or_build_index(base_path: Path, background_tasks: BackgroundTasks) -> None:
    """
    Get the in-memory index or trigger a rebuild if necessary.

    Args:
        base_path: The root directory.
        background_tasks: FastAPI BackgroundTasks object to schedule rebuild.
    """
    index_status = IndexStatus()
    # If index is already valid and not too old (24 hours), don't rebuild
    if index_status.is_valid and index_status.created_at:
        age = datetime.now() - index_status.created_at
        if age.total_seconds() <= 24 * 3600:
            return None

    # If not already building, start the build process
    if not index_status.is_building:
        index_status.is_building = True
        background_tasks.add_task(build_and_save_index, base_path)
    return None
