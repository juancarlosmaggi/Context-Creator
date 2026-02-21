from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from datetime import datetime
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

    # Pre-calculate strings for performance in loops
    base_path_str = str(base_path)
    git_root_str = str(git_root) if git_root else None

    def process_directory(path: Union[Path, str], parent_children_list: List[Dict[str, Any]], depth: int = 0) -> List[Tuple[str, List[Dict[str, Any]], int]]:
        """
        Scan a single directory, populate parent_children_list, and return subdirectories to process.
        """
        sub_dirs = []
        try:
            entries_data = []
            with os.scandir(path) as it:
                for scandir_entry in it:
                    is_entry_dir = scandir_entry.is_dir()
                    if should_ignore(scandir_entry.path, base_path_str, git_root_str, ignore_spec, context_ignore_spec, is_dir=is_entry_dir):
                        continue
                    entries_data.append((scandir_entry, is_entry_dir))

            # Sort directories first, then files, both alphabetically
            entries_data.sort(key=lambda x: (not x[1], x[0].name.lower()))

            for scandir_entry, is_entry_dir in entries_data:
                # Calculate relative path efficiently using string manipulation
                # scandir_entry.path is an absolute string

                entry_path_str = scandir_entry.path
                if entry_path_str.startswith(base_path_str):
                    rel_path = entry_path_str[len(base_path_str):]
                    if rel_path.startswith(os.sep):
                        rel_path = rel_path[1:]
                else:
                    # Fallback for unexpected paths
                    rel_path = str(Path(entry_path_str).relative_to(base_path))

                rel_path = rel_path.replace("\\", "/")

                entry = {
                    "path": rel_path,
                    "name": scandir_entry.name,
                    "type": "directory" if is_entry_dir else "file",
                    "children": []
                }
                parent_children_list.append(entry)

                if is_entry_dir:
                    # Bounded parallelism: only submit tasks for the first few levels
                    # to avoid overhead of creating too many small tasks.
                    if depth < 2:
                        sub_dirs.append((entry_path_str, entry["children"], depth + 1))
                    else:
                        # Recurse immediately in the current thread
                        process_directory(entry_path_str, entry["children"], depth + 1)

        except (PermissionError, OSError):
            pass

        return sub_dirs

    root_entry = {
        "path": "",
        "name": base_path.name,
        "type": "directory",
        "children": []
    }

    # We use a ThreadPoolExecutor to process directories in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = set()

        # Submit the initial task
        futures.add(executor.submit(process_directory, base_path_str, root_entry["children"], 0))

        while futures:
            # Wait for at least one future to complete
            done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                try:
                    new_tasks = future.result()
                    for task_path, task_list, task_depth in new_tasks:
                        futures.add(executor.submit(process_directory, task_path, task_list, task_depth))
                except Exception:
                    # Log error if needed, but ensure we don't crash everything
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
