import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from context_creator.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def temp_project():
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)

    # Create some files and directories
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

    yield base_path

    shutil.rmtree(temp_dir)
