
import os
import sys
import shutil
import tempfile
from pathlib import Path
from types import ModuleType

# Mock pathspec if missing
try:
    import pathspec
except ImportError:
    m = ModuleType("pathspec")
    class MockPathSpec:
        def __init__(self, *args, **kwargs):
            self.patterns = []
        @staticmethod
        def from_lines(type, patterns):
            import re
            class MockPathSpecInternal:
                def __init__(self, patterns):
                    self.patterns = patterns
                def match_file(self, path):
                    # Very basic glob-like matching for test purposes
                    for p in self.patterns:
                        if p.startswith("*"):
                            if path.endswith(p[1:]): return True
                        if p.startswith("/"):
                            if path.startswith(p[1:]): return True
                        if p in path: return True
                    return False
            return MockPathSpecInternal(patterns)
    m.PathSpec = MockPathSpec
    sys.modules["pathspec"] = m
    import pathspec

# Add the project root to sys.path to import context_creator
sys.path.append(os.getcwd())

from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)

def run_tests():
    temp_dir = tempfile.mkdtemp()
    try:
        base_path = Path(temp_dir)
        (base_path / ".git").mkdir()
        (base_path / "src").mkdir()
        (base_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (base_path / "README.md").write_text("# Test Project", encoding="utf-8")
        (base_path / ".gitignore").write_text("*.log\n/temp/", encoding="utf-8")
        (base_path / ".contextignore").write_text("secrets.txt", encoding="utf-8")
        (base_path / "test.log").write_text("log content", encoding="utf-8")
        (base_path / "secrets.txt").write_text("secret", encoding="utf-8")
        (base_path / "temp").mkdir()
        (base_path / "temp" / "temp_file.txt").write_text("temp", encoding="utf-8")

        print("Testing find_git_root...")
        assert find_git_root(base_path) == base_path.resolve()
        assert find_git_root(base_path / "src") == base_path.resolve()

        print("Testing should_ignore...")
        git_root = base_path
        ignore_spec = parse_gitignore(base_path)
        context_ignore_spec = parse_contextignore(base_path)

        # Ignored by .gitignore
        assert should_ignore(base_path / "test.log", base_path, git_root, ignore_spec, context_ignore_spec)
        # Ignored by .contextignore
        assert should_ignore(base_path / "secrets.txt", base_path, git_root, ignore_spec, context_ignore_spec)
        # Hidden files
        assert should_ignore(base_path / ".git", base_path, git_root, ignore_spec, context_ignore_spec)
        # Not ignored
        assert not should_ignore(base_path / "src" / "main.py", base_path, git_root, ignore_spec, context_ignore_spec)

        print("Testing with pre-computed prefixes...")
        sep = os.sep
        base_path_str = str(base_path)
        git_root_str = str(git_root)
        base_path_prefix = base_path_str if base_path_str.endswith(sep) else base_path_str + sep
        git_root_prefix = git_root_str if git_root_str.endswith(sep) else git_root_str + sep

        assert should_ignore(base_path / "test.log", base_path_str, git_root_str, ignore_spec, context_ignore_spec, base_path_prefix=base_path_prefix, git_root_prefix=git_root_prefix)
        assert not should_ignore(base_path / "src" / "main.py", base_path_str, git_root_str, ignore_spec, context_ignore_spec, base_path_prefix=base_path_prefix, git_root_prefix=git_root_prefix)

        print("All manual tests passed!")
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    run_tests()
