from typing import Union, Optional, List
from pathlib import Path
from functools import lru_cache
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

    # Then process all other .gitignore files
    for gitignore_path in git_root.glob("*/**/.gitignore"): # Skip root .gitignore we processed above
        try:
            relative_dir = gitignore_path.parent.relative_to(git_root)
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
        except (ValueError, OSError, UnicodeDecodeError):
            continue

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
    path: Path,
    base_path: Path,
    git_root: Optional[Path],
    ignore_spec: Optional[pathspec.PathSpec],
    context_ignore_spec: pathspec.PathSpec
) -> bool:
    """
    Determine if a path should be ignored based on .gitignore and .contextignore rules.

    Args:
        path: The path to check.
        base_path: The base path of the project.
        git_root: The git root directory (if any).
        ignore_spec: The PathSpec for gitignore patterns.
        context_ignore_spec: The PathSpec for contextignore patterns.

    Returns:
        True if the path should be ignored, False otherwise.
    """
    # Always ignore hidden files/dirs
    if path.name.startswith("."):
        return True

    # Check against gitignore patterns
    if git_root and ignore_spec:
        try:
            if path.is_relative_to(git_root):
                rel_path = path.relative_to(git_root)
                # Check both the path and the path with trailing slash for directories
                if ignore_spec.match_file(rel_path):
                    return True
                if path.is_dir() and ignore_spec.match_file(str(rel_path) + '/'):
                    return True
        except ValueError:
            pass

    # Check against contextignore patterns
    if context_ignore_spec:
        try:
            if path.is_relative_to(base_path):
                rel_path = path.relative_to(base_path)
                if context_ignore_spec.match_file(rel_path):
                    return True
                if path.is_dir() and context_ignore_spec.match_file(str(rel_path) + '/'):
                    return True
        except ValueError:
            pass

    return False
