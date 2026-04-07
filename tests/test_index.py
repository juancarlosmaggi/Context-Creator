import tempfile
from pathlib import Path
import pytest

import context_creator.core.index as index_module
from context_creator.core.index import get_project_structure, get_token_count

def test_get_project_structure_correctness():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure:
        # root/
        #   dir1/
        #     file1.txt
        #   file2.txt

        (temp_path / "dir1").mkdir()
        (temp_path / "dir1" / "file1.txt").write_text("hello from file one", encoding="utf-8")
        (temp_path / "file2.txt").write_text("hello from file two", encoding="utf-8")

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
        assert children[0]["children"][0]["tokens"] > 0

        assert children[1]["name"] == "file2.txt"
        assert children[1]["type"] == "file"
        assert children[1]["tokens"] > 0


def test_get_token_count_raises_when_tiktoken_init_fails(monkeypatch, tmp_path):
    temp_file_path = tmp_path / "sample.txt"
    temp_file_path.write_text("token counting should fail loudly", encoding="utf-8")

    monkeypatch.setattr(index_module, "_enc", None)

    def fail_encoding():
        raise RuntimeError("unable to load bundled cl100k_base encoding")

    monkeypatch.setattr(index_module, "get_encoding", fail_encoding)

    with pytest.raises(RuntimeError, match="unable to load bundled cl100k_base encoding"):
        get_token_count(str(temp_file_path))


def test_get_token_count_handles_literal_special_token_strings(tmp_path):
    temp_file_path = tmp_path / "special-tokens.txt"
    temp_file_path.write_text("literal <|endoftext|> token in source", encoding="utf-8")

    assert get_token_count(str(temp_file_path)) > 0
