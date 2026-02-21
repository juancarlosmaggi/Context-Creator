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

    # Create a spec for pruning based on root .gitignore
    # This spec is used to skip traversing into ignored directories
    # We maintain a list of active specs to support nested .gitignore files
    prune_specs = [pathspec.PathSpec.from_lines("gitignore", patterns)]

    # Then process all other .gitignore files using os.walk for controlled traversal
    # We prune directories that are ignored by the root .gitignore or any nested .gitignore found
    for root, dirs, files in os.walk(git_root):
        root_path = Path(root)

        # Check for .gitignore in current directory
        # Skip the root .gitignore as we already processed it
        if root_path != git_root and ".gitignore" in files:
            gitignore_path = root_path / ".gitignore"
            try:
                relative_dir = root_path.relative_to(git_root)
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    # For patterns that don't start with '/', prefix with the directory path
                    adjusted = []
                    for line in lines:
                        if line.startswith('/'):
                            # This is a directory-specific absolute pattern, make it relative to this directory
                            adjusted.append(str(relative_dir / line[1:]))
                        else:
                            # This is already a pattern relative to the .gitignore location
                            adjusted.append(str(relative_dir / line))
                    patterns.extend(adjusted)

                    # Add new spec to prune_specs to filter subdirectories of this directory
                    prune_specs.append(pathspec.PathSpec.from_lines("gitignore", adjusted))
            except (ValueError, OSError, UnicodeDecodeError):
                pass

        # Modify dirs in-place to prune traversal
        # 1. Remove hidden directories (starting with .)
        # 2. Remove directories ignored by any active ignore spec

        # Iterate backwards to safely remove from list
        for i in range(len(dirs) - 1, -1, -1):
            d = dirs[i]
            if d.startswith("."):
                del dirs[i]
                continue

            dir_abs = root_path / d
            try:
                # Calculate path relative to git_root for checking against prune_specs
                rel_path = dir_abs.relative_to(git_root)
                rel_path_str = str(rel_path)

                # Check if the directory itself is ignored by ANY known spec
                is_ignored = False
                for spec in prune_specs:
                    if spec.match_file(rel_path_str) or spec.match_file(rel_path_str + "/"):
                        is_ignored = True
                        break

                if is_ignored:
                    del dirs[i]
            except ValueError:
                # Should not happen if we are traversing under git_root
                pass

    return pathspec.PathSpec.from_lines("gitignore", patterns)

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
