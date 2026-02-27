
import timeit
import os
from pathlib import Path
import pathspec
from context_creator.core.ignore import should_ignore

# Setup
git_root = Path("/tmp/test_repo")
base_path = git_root
ignore_spec = pathspec.PathSpec.from_lines("gitignore", ["*.pyc", "__pycache__", "node_modules"])
context_ignore_spec = pathspec.PathSpec.from_lines("gitignore", ["*.log"])

# Create dummy paths
paths = []
for i in range(1000):
    paths.append(str(git_root / f"dir_{i}" / "file.py"))
    paths.append(str(git_root / f"dir_{i}" / "ignored.pyc"))
    paths.append(str(git_root / "node_modules" / f"pkg_{i}" / "index.js"))

git_root_str = str(git_root)
base_path_str = str(base_path)

def run_benchmark():
    count = 0
    for p in paths:
        if should_ignore(p, base_path_str, git_root_str, ignore_spec, context_ignore_spec, is_dir=False, name=os.path.basename(p)):
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
