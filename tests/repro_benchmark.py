
import timeit
import os
import sys
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
            return MockPathSpec()
        def match_file(self, path):
            return False
    m.PathSpec = MockPathSpec
    sys.modules["pathspec"] = m
    import pathspec

# Add the project root to sys.path to import context_creator
sys.path.append(os.getcwd())

from context_creator.core.ignore import should_ignore

# Setup
git_root_path = Path("/tmp/test_repo")
base_path_path = git_root_path
ignore_spec = pathspec.PathSpec.from_lines("gitignore", ["*.pyc", "__pycache__", "node_modules"])
context_ignore_spec = pathspec.PathSpec.from_lines("gitignore", ["*.log"])

# Create dummy paths
paths = []
for i in range(1000):
    paths.append(str(git_root_path / f"dir_{i}" / "file.py"))
    paths.append(str(git_root_path / f"dir_{i}" / "ignored.pyc"))
    paths.append(str(git_root_path / "node_modules" / f"pkg_{i}" / "index.js"))

git_root_str = str(git_root_path)
base_path_str = str(base_path_path)

def run_benchmark():
    count = 0
    sep = os.sep
    base_path_prefix = base_path_str if base_path_str.endswith(sep) else base_path_str + sep
    git_root_prefix = git_root_str if git_root_str.endswith(sep) else git_root_str + sep
    for p in paths:
        if should_ignore(p, base_path_str, git_root_str, ignore_spec, context_ignore_spec, is_dir=False, name=os.path.basename(p), base_path_prefix=base_path_prefix, git_root_prefix=git_root_prefix):
            count += 1
    return count

if __name__ == "__main__":
    # Warmup
    run_benchmark()

    # Measure
    number = 100
    time = timeit.timeit(run_benchmark, number=number)
    print(f"Time for {number} runs processing {len(paths)} paths: {time:.4f}s")
    print(f"Time per run: {time/number:.4f}s")
    print(f"Time per path: {(time/number/len(paths))*1_000_000:.2f}us")
