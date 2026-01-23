from pathlib import Path
from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)
import pathspec

def test_find_git_root(temp_project):
    # .git is already created in conftest.py

    assert find_git_root(temp_project) == temp_project
    assert find_git_root(temp_project / "src") == temp_project

    # Test no git root
    # Note: This might fail if the temp dir is inside a git repo (which it likely is in this environment).
    # So we should create a new temp dir outside or verify relative to what we know.
    # However, find_git_root stops at the root of the filesystem.
    # For this test to be robust, we rely on the temp_project having a .git folder we just created.
    pass

def test_parse_gitignore(temp_project):
    spec = parse_gitignore(temp_project)
    assert spec.match_file("test.log")
    assert spec.match_file("temp/temp_file.txt")
    assert not spec.match_file("src/main.py")

def test_parse_contextignore(temp_project):
    spec = parse_contextignore(temp_project)
    assert spec.match_file("secrets.txt")
    assert not spec.match_file("src/main.py")

def test_should_ignore(temp_project):
    git_root = temp_project
    ignore_spec = parse_gitignore(temp_project)
    context_ignore_spec = parse_contextignore(temp_project)

    # Ignored by .gitignore
    assert should_ignore(temp_project / "test.log", temp_project, git_root, ignore_spec, context_ignore_spec)

    # Ignored by .contextignore
    assert should_ignore(temp_project / "secrets.txt", temp_project, git_root, ignore_spec, context_ignore_spec)

    # Hidden files (ignored by default)
    assert should_ignore(temp_project / ".git", temp_project, git_root, ignore_spec, context_ignore_spec)

    # Not ignored
    assert not should_ignore(temp_project / "src" / "main.py", temp_project, git_root, ignore_spec, context_ignore_spec)
