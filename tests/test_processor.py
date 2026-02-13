from context_creator.core.processor import process_files

def test_process_files(temp_project):
    # Select some files
    selected_paths = ["src/main.py", "README.md"]

    output = "".join(process_files(selected_paths, temp_project))

    assert "# File" in output
    assert "src/main.py" in output
    assert "print('hello')" in output
    assert "README.md" in output
    assert "# Test Project" in output

def test_process_files_ignore(temp_project):
    # Try to process ignored file
    selected_paths = ["test.log"]

    output = "".join(process_files(selected_paths, temp_project))

    # Should be empty or not contain the ignored file content if logic prevents it
    # The processor logic iterates selected paths and checks should_ignore.
    # If explicit path is given but it matches ignore, it should be skipped.
    assert "log content" not in output
