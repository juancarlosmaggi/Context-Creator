
import tempfile
from pathlib import Path
from context_creator.core.index import get_project_structure

def test_get_project_structure_correctness():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure:
        # root/
        #   dir1/
        #     file1.txt
        #   file2.txt

        (temp_path / "dir1").mkdir()
        (temp_path / "dir1" / "file1.txt").touch()
        (temp_path / "file2.txt").touch()

        structure = get_project_structure(temp_path)

        assert structure["name"] == temp_path.name
        assert structure["type"] == "directory"

        children = structure["children"]
        assert len(children) == 2

        # Check sorting: dir1 should be first because dirs are sorted before files
        assert children[0]["name"] == "dir1"
        assert children[0]["type"] == "directory"
        assert len(children[0]["children"]) == 1
        assert children[0]["children"][0]["name"] == "file1.txt"

        assert children[1]["name"] == "file2.txt"
        assert children[1]["type"] == "file"
