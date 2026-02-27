
import timeit
import os
import stat
from pathlib import Path
from context_creator.core.ignore import should_ignore, find_git_root, parse_gitignore, parse_contextignore

# Setup environment
base_path = Path.cwd()
git_root = find_git_root(base_path)
ignore_spec = parse_gitignore(git_root) if git_root else None
context_ignore_spec = parse_contextignore(base_path)

# Create a temporary file for testing
test_file = base_path / "benchmark_test_file.txt"
test_file.touch()

# Create a temporary directory for testing
test_dir = base_path / "benchmark_test_dir"
test_dir.mkdir(exist_ok=True)

test_path_file = "benchmark_test_file.txt"
full_path_file = base_path / test_path_file

test_path_dir = "benchmark_test_dir"
full_path_dir = base_path / test_path_dir

def current_implementation(full_path):
    # Mimics the code in context_creator/main.py:51
    return {
        "path": str(full_path),
        "is_ignored": should_ignore(full_path, base_path, git_root, ignore_spec, context_ignore_spec, name=full_path.name),
        "exists": full_path.exists(),
        "is_dir": full_path.is_dir() if full_path.exists() else None,
    }

def optimized_implementation(full_path):
    # Proposed optimization
    try:
        stat_result = full_path.stat()
        exists = True
        is_dir = stat.S_ISDIR(stat_result.st_mode)
    except FileNotFoundError:
        exists = False
        is_dir = None

    return {
        "path": str(full_path),
        "is_ignored": should_ignore(full_path, base_path, git_root, ignore_spec, context_ignore_spec, is_dir=is_dir, name=full_path.name),
        "exists": exists,
        "is_dir": is_dir,
    }

def run_benchmark():
    iterations = 1000

    # Benchmark with a file
    t_current_file = timeit.timeit(lambda: current_implementation(full_path_file), number=iterations)
    t_optimized_file = timeit.timeit(lambda: optimized_implementation(full_path_file), number=iterations)

    # Benchmark with a directory
    t_current_dir = timeit.timeit(lambda: current_implementation(full_path_dir), number=iterations)
    t_optimized_dir = timeit.timeit(lambda: optimized_implementation(full_path_dir), number=iterations)

    print(f"Benchmark results ({iterations} iterations):")
    print(f"File - Current: {t_current_file:.6f}s")
    print(f"File - Optimized: {t_optimized_file:.6f}s")
    if t_current_file > 0:
        print(f"File - Improvement: {(t_current_file - t_optimized_file) / t_current_file * 100:.2f}%")
    else:
        print("File - Too fast to measure improvement")

    print(f"Dir - Current: {t_current_dir:.6f}s")
    print(f"Dir - Optimized: {t_optimized_dir:.6f}s")
    if t_current_dir > 0:
        print(f"Dir - Improvement: {(t_current_dir - t_optimized_dir) / t_current_dir * 100:.2f}%")
    else:
        print("Dir - Too fast to measure improvement")

if __name__ == "__main__":
    try:
        run_benchmark()
    finally:
        if test_file.exists():
            test_file.unlink()
        if test_dir.exists():
            test_dir.rmdir()
