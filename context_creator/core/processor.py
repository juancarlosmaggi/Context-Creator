import os
import concurrent.futures
from pathlib import Path
from typing import List, Set

from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)

def process_files(selected_paths: List[str], base_path: Path) -> str:
    """
    Process selected files and directories into a single text output.

    Args:
        selected_paths: List of relative paths to process.
        base_path: The base directory of the project.

    Returns:
        A string containing the formatted content of all selected files.
    """
    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    context_ignore_spec = parse_contextignore(base_path)

    def process_file(file_path: Path) -> str:
        relative_path = file_path.relative_to(base_path)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024: # Skip files > 10MB
                size_mb = file_path.stat().st_size / 1024 / 1024
                return f"# File\n\n```text\n{relative_path}\n```\n\n# Content\n\n```text\n[File too large - {size_mb:.2f} MB]\n```\n\n"

            # Get file extension for markdown syntax highlighting
            ext = file_path.suffix.lower()
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.jsx': 'jsx',
                '.ts': 'typescript',
                '.tsx': 'tsx',
                '.php': 'php',
                '.html': 'html',
                '.css': 'css',
                '.scss': 'scss',
                '.json': 'json',
                '.md': 'markdown',
                '.sh': 'bash',
                '.go': 'go',
                '.rs': 'rust',
                '.java': 'java',
                '.kt': 'kotlin',
                '.swift': 'swift',
                '.rb': 'ruby',
                '.c': 'c',
                '.cpp': 'cpp',
                '.h': 'cpp',
                '.cs': 'csharp',
                '.m': 'objectivec',
                '.pl': 'perl',
                '.lua': 'lua',
                '.sql': 'sql',
                '.xml': 'xml',
                '.yaml': 'yaml',
                '.yml': 'yaml',
                '.toml': 'toml',
                '.ini': 'ini',
                '.cfg': 'ini',
                '.conf': 'ini',
            }
            lang = lang_map.get(ext, 'text')

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return f"# File\n\n```text\n{relative_path}\n```\n\n# Content\n\n```{lang}\n{content}\n```\n\n"
        except (UnicodeDecodeError, PermissionError, OSError):
            return f"# File\n\n```text\n{relative_path}\n```\n\n# Content\n\n```text\n[Unable to process file]\n```\n\n"

    all_files: Set[Path] = set()
    for path_str in selected_paths:
        path = Path(path_str)
        # Handle cases where path might be absolute or relative incorrectly
        # We assume selected_paths are relative to base_path
        full_path = base_path / path

        if full_path.exists():
            if full_path.is_file():
                if not should_ignore(full_path, base_path, git_root, ignore_spec, context_ignore_spec):
                    all_files.add(full_path)
            elif full_path.is_dir():
                # Use os.walk with in-place pruning of dirs to avoid traversing ignored directories
                # This is significantly faster than rglob which traverses everything before filtering
                # Using strings instead of Path objects during traversal significantly reduces overhead
                full_path_str = str(full_path)
                for root, dirs, files in os.walk(full_path_str):
                    # Modify dirs in-place to skip ignored directories
                    for i in range(len(dirs) - 1, -1, -1):
                        d = dirs[i]
                        d_path_str = os.path.join(root, d)
                        if should_ignore(d_path_str, base_path, git_root, ignore_spec, context_ignore_spec):
                            del dirs[i]

                    for f in files:
                        f_path_str = os.path.join(root, f)
                        if not should_ignore(f_path_str, base_path, git_root, ignore_spec, context_ignore_spec):
                            all_files.add(Path(f_path_str))

    sorted_files = sorted(list(all_files), key=lambda f: str(f.relative_to(base_path)))

    # Limit max workers
    max_workers = min(32, (os.cpu_count() or 1) * 4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_file, sorted_files))

    return "".join(results)
