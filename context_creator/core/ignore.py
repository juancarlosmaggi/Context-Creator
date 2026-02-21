from typing import Union, Optional, List
from pathlib import Path
from functools import lru_cache
import os
import pathspec

def find_git_root(path: Path) -> Optional[Path]:
    """
    Find the nearest parent directory containing a .git folder.

    Args:
        path: The starting path.

    Returns:
        The path to the git root directory if found, otherwise None.
    """
    try:
        current = path.resolve()
        while True:
            if (current / ".git").exists():
                return current
            if current.parent == current:
                return None
            current = current.parent
    except Exception:
        return None

@lru_cache()
def parse_gitignore(git_root: Path) -> pathspec.PathSpec:
    """
    Parse all .gitignore files in the repository into a PathSpec.

    Args:
        git_root: The root directory of the git repository.

    Returns:
        A PathSpec object containing all gitignore patterns.
    """
    patterns: List[str] = []

    # First process the root .gitignore
    root_gitignore = git_root / ".gitignore"
    if root_gitignore.exists():
        try:
            with open(root_gitignore, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                patterns.extend(lines)
        except (OSError, UnicodeDecodeError):
            pass

    # Initial spec from root .gitignore
    root_spec = pathspec.PathSpec.from_lines("gitignore", patterns)

    # Use stack-based traversal to prune efficiently
    # Stack stores: (current_directory_path, list_of_active_specs)
    stack = [(git_root, [root_spec])]

    while stack:
        current_path, current_specs = stack.pop()

        try:
            # os.scandir is generally faster and gives us DirEntry objects
            with os.scandir(current_path) as it:
                entries = list(it)
        except OSError:
            continue

        # Check for .gitignore in current directory
        # Skip root .gitignore as we already processed it
        gitignore_entry = next((e for e in entries if e.name == ".gitignore" and e.is_file()), None)

        next_specs = current_specs
        if gitignore_entry and current_path != git_root:
            try:
                relative_dir = current_path.relative_to(git_root)
                with open(gitignore_entry.path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

                    adjusted = []
                    for line in lines:
                        if line.startswith('/'):
                            # Directory-specific absolute pattern, make relative to git_root
                            # line[1:] removes leading slash
                            adjusted.append(str(relative_dir / line[1:]))
                        else:
                            # Pattern relative to .gitignore location
                            adjusted.append(str(relative_dir / line))

                    patterns.extend(adjusted)
                    # Create new spec for this directory's rules and add to active specs
                    new_spec = pathspec.PathSpec.from_lines("gitignore", adjusted)
                    next_specs = current_specs + [new_spec]
            except (ValueError, OSError, UnicodeDecodeError):
                pass

        # Filter directories to traverse
        # We iterate in reverse to mimic stack behavior if we want depth-first
        # (though order usually doesn't strictly matter for correctness here)
        # We must NOT follow symlinks to avoid infinite loops and match os.walk default behavior
        dirs = [e for e in entries if e.is_dir(follow_symlinks=False)]

        for entry in dirs:
            if entry.name.startswith("."):
                continue

            entry_path = Path(entry.path)
            try:
                rel_path = entry_path.relative_to(git_root)
                rel_path_str = str(rel_path)

                is_ignored = False
                for spec in next_specs:
                    if spec.match_file(rel_path_str) or spec.match_file(rel_path_str + "/"):
                        is_ignored = True
                        break

                if not is_ignored:
                    stack.append((entry_path, next_specs))
            except ValueError:
                pass

    return pathspec.PathSpec.from_lines("gitignore", patterns)

@lru_cache()
def parse_contextignore(base_path: Path) -> pathspec.PathSpec:
    """
    Parse .contextignore file at the base path into a PathSpec.

    Args:
        base_path: The base directory where .contextignore is located.

    Returns:
        A PathSpec object containing all contextignore patterns.
    """
    patterns: List[str] = []
    contextignore_path = base_path / ".contextignore"
    if contextignore_path.exists():
        try:
            with open(contextignore_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                patterns.extend(lines)
        except (OSError, UnicodeDecodeError):
            pass
    return pathspec.PathSpec.from_lines("gitignore", patterns)

def should_ignore(
    path: Union[Path, str],
    base_path: Union[Path, str],
    git_root: Optional[Union[Path, str]],
    ignore_spec: Optional[pathspec.PathSpec],
    context_ignore_spec: pathspec.PathSpec,
    is_dir: Optional[bool] = None
) -> bool:
    """
    Determine if a path should be ignored based on .gitignore and .contextignore rules.

    Args:
        path: The path to check.
        base_path: The base path of the project.
        git_root: The git root directory (if any).
        ignore_spec: The PathSpec for gitignore patterns.
        context_ignore_spec: The PathSpec for contextignore patterns.
        is_dir: Whether the path is a directory (optional optimization to avoid syscall).

    Returns:
        True if the path should be ignored, False otherwise.
    """
    if isinstance(path, str):
        name = os.path.basename(path)
        # Optimized string handling
        path_str = path
        if is_dir is None:
            is_dir = os.path.isdir(path)
    else:
        name = path.name
        path_str = str(path)
        if is_dir is None:
            is_dir = path.is_dir()

    # Always ignore hidden files/dirs
    if name.startswith("."):
        return True

    # Check against gitignore patterns
    if git_root and ignore_spec:
        try:
            if isinstance(git_root, str):
                git_root_str = git_root
            else:
                git_root_str = str(git_root)

            if path_str == git_root_str:
                rel_path_str = "."
                if ignore_spec.match_file(rel_path_str):
                    return True
                if is_dir and ignore_spec.match_file(rel_path_str + '/'):
                    return True
            else:
                sep = os.sep
                prefix = git_root_str if git_root_str.endswith(sep) else git_root_str + sep
                if path_str.startswith(prefix):
                    rel_path_str = path_str[len(prefix):]
                    if ignore_spec.match_file(rel_path_str):
                        return True
                    if is_dir and ignore_spec.match_file(rel_path_str + '/'):
                        return True
        except (ValueError, TypeError):
            pass

    # Check against contextignore patterns
    if context_ignore_spec:
        try:
            if isinstance(base_path, str):
                base_path_str = base_path
            else:
                base_path_str = str(base_path)

            if path_str == base_path_str:
                rel_path_str = "."
                if context_ignore_spec.match_file(rel_path_str):
                    return True
                if is_dir and context_ignore_spec.match_file(rel_path_str + '/'):
                    return True
            else:
                sep = os.sep
                prefix = base_path_str if base_path_str.endswith(sep) else base_path_str + sep
                if path_str.startswith(prefix):
                    rel_path_str = path_str[len(prefix):]
                    if context_ignore_spec.match_file(rel_path_str):
                        return True
                    if is_dir and context_ignore_spec.match_file(rel_path_str + '/'):
                        return True
        except (ValueError, TypeError):
            pass

    return False
