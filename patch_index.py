import re

with open("context_creator/core/index.py", "r") as f:
    content = f.read()

# Add tiktoken import
if "import tiktoken" not in content:
    content = content.replace("import concurrent.futures", "import concurrent.futures\nimport tiktoken")

# Initialize encoding
init_enc = """
# Initialize tiktoken encoding globally to avoid recreation overhead
try:
    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:
    _enc = None

def get_token_count(file_path: str) -> int:
    if not _enc:
        return 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return len(_enc.encode(content))
    except Exception:
        return 0
"""

if "def get_token_count" not in content:
    content = content.replace("class IndexStatus:", init_enc + "\nclass IndexStatus:")

# Update the entry creation in process_directory
replacement = """
                entry = {
                    "path": rel_path,
                    "name": scandir_entry.name,
                    "type": "directory" if is_entry_dir else "file",
                    "children": []
                }

                if not is_entry_dir:
                    entry["tokens"] = get_token_count(entry_path_str)
"""

content = re.sub(r'entry\s*=\s*\{\s*"path":\s*rel_path,\s*"name":\s*scandir_entry\.name,\s*"type":\s*"directory"\s*if\s*is_entry_dir\s*else\s*"file",\s*"children":\s*\[\]\s*\}', replacement, content)

with open("context_creator/core/index.py", "w") as f:
    f.write(content)
