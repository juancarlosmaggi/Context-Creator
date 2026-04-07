from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from datetime import datetime
import concurrent.futures
from importlib.resources import as_file, files
import json
import tiktoken
import os
import threading
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from tiktoken.load import load_tiktoken_bpe

from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)


CL100K_BASE_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
CL100K_BASE_PAT_STR = r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""
CL100K_BASE_SPECIAL_TOKENS = {
    "<|endoftext|>": 100257,
    "<|fim_prefix|>": 100258,
    "<|fim_middle|>": 100259,
    "<|fim_suffix|>": 100260,
    "<|endofprompt|>": 100276,
}
TOKEN_CACHE_VERSION = 1
TOKEN_CACHE_FILENAME = "context_creator_tokens.json"

_enc: Optional[tiktoken.Encoding] = None


def get_encoding() -> tiktoken.Encoding:
    """Load the bundled cl100k_base encoding without any network dependency."""
    global _enc
    if _enc is not None:
        return _enc

    bpe_resource = files("context_creator").joinpath("data", "cl100k_base.tiktoken")
    with as_file(bpe_resource) as bpe_path:
        mergeable_ranks = load_tiktoken_bpe(str(bpe_path), expected_hash=CL100K_BASE_HASH)

    _enc = tiktoken.Encoding(
        name="cl100k_base",
        pat_str=CL100K_BASE_PAT_STR,
        mergeable_ranks=mergeable_ranks,
        special_tokens=CL100K_BASE_SPECIAL_TOKENS,
    )
    return _enc

def get_token_count(file_path: str) -> int:
    try:
        # Don't try to encode files larger than 1MB to prevent blocking the event loop
        if os.path.getsize(file_path) > 1 * 1024 * 1024:
            return 0

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return len(get_encoding().encode(content, disallowed_special=()))
    except (UnicodeDecodeError, PermissionError, OSError):
        return 0


def get_token_cache_path(base_path: Path) -> Path:
    return base_path / ".cache" / TOKEN_CACHE_FILENAME


def load_token_cache(base_path: Path) -> Dict[str, Dict[str, int]]:
    cache_path = get_token_cache_path(base_path)
    if not cache_path.exists():
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        return {}

    if payload.get("version") != TOKEN_CACHE_VERSION:
        return {}
    if payload.get("encoding_hash") != CL100K_BASE_HASH:
        return {}

    files_payload = payload.get("files")
    if not isinstance(files_payload, dict):
        return {}
    return files_payload


def save_token_cache(base_path: Path, token_cache: Dict[str, Dict[str, int]]) -> None:
    cache_path = get_token_cache_path(base_path)
    cache_path.parent.mkdir(exist_ok=True)
    payload = {
        "version": TOKEN_CACHE_VERSION,
        "encoding_hash": CL100K_BASE_HASH,
        "files": token_cache,
    }
    temp_path = cache_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as cache_file:
        json.dump(payload, cache_file, separators=(",", ":"))
    os.replace(temp_path, cache_path)

class IndexStatus:
    """Singleton class to store the project index status."""
    _instance = None
    is_building: bool = False
    is_valid: bool = False
    structure: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    error: Optional[str] = None

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
    # Fail the build immediately if tiktoken itself is not healthy.
    get_encoding()

    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    context_ignore_spec = parse_contextignore(base_path)
    token_cache = load_token_cache(base_path)
    token_cache_lock = threading.Lock()
    seen_files = set()

    # Pre-calculate strings for performance in loops
    base_path_str = str(base_path)
    base_path_prefix = base_path_str if base_path_str.endswith(os.sep) else base_path_str + os.sep
    git_root_str = str(git_root) if git_root else None

    def get_cached_token_count(file_path: str, relative_path: str, file_size: int, file_mtime_ns: int) -> int:
        with token_cache_lock:
            cached = token_cache.get(relative_path)
            if (
                cached
                and cached.get("size") == file_size
                and cached.get("mtime_ns") == file_mtime_ns
            ):
                seen_files.add(relative_path)
                return int(cached["tokens"])

        token_count = get_token_count(file_path)

        with token_cache_lock:
            token_cache[relative_path] = {
                "size": file_size,
                "mtime_ns": file_mtime_ns,
                "tokens": token_count,
            }
            seen_files.add(relative_path)

        return token_count

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
                    if should_ignore(scandir_entry.path, base_path_str, git_root_str, ignore_spec, context_ignore_spec, is_dir=is_entry_dir, name=scandir_entry.name):
                        continue
                    entries_data.append((scandir_entry, is_entry_dir))

            # Sort directories first, then files, both alphabetically
            entries_data.sort(key=lambda x: (not x[1], x[0].name.lower()))

            for scandir_entry, is_entry_dir in entries_data:
                # Calculate relative path efficiently using string manipulation
                # scandir_entry.path is an absolute string

                entry_path_str = scandir_entry.path
                if entry_path_str.startswith(base_path_prefix):
                    rel_path = entry_path_str[len(base_path_prefix):]
                elif entry_path_str == base_path_str:
                    rel_path = ""
                else:
                    # Fallback for unexpected paths
                    rel_path = os.path.relpath(entry_path_str, base_path_str)

                rel_path = rel_path.replace("\\", "/")


                entry = {
                    "path": rel_path,
                    "name": scandir_entry.name,
                    "type": "directory" if is_entry_dir else "file",
                    "children": []
                }

                if not is_entry_dir:
                    file_stat = scandir_entry.stat(follow_symlinks=False)
                    entry["tokens"] = get_cached_token_count(
                        entry_path_str,
                        rel_path,
                        file_stat.st_size,
                        file_stat.st_mtime_ns,
                    )

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
                new_tasks = future.result()
                for task_path, task_list, task_depth in new_tasks:
                    futures.add(executor.submit(process_directory, task_path, task_list, task_depth))

    with token_cache_lock:
        pruned_cache = {path: token_cache[path] for path in seen_files if path in token_cache}
    save_token_cache(base_path, pruned_cache)

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
        index_status.error = None
    except Exception as exc:
        index_status.structure = None
        index_status.is_valid = False
        index_status.error = str(exc)
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
        index_status.error = None
        background_tasks.add_task(build_and_save_index, base_path)
    return None
