from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from datetime import datetime
import pathspec

def find_git_root(path: Path) -> Path | None:
    """Find the nearest parent directory containing a .git folder"""
    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent
    return None

def parse_gitignore(git_root: Path) -> pathspec.PathSpec:
    """Parse all .gitignore files in the repository into a PathSpec"""
    spec = pathspec.PathSpec([])
    for gitignore_path in git_root.glob("**/.gitignore"):
        relative_dir = gitignore_path.parent.relative_to(git_root)
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                # Adjust patterns to be relative to repository root
                adjusted = [str(relative_dir / line) if relative_dir != Path('.') else line 
                            for line in lines]
                spec += pathspec.PathSpec.from_lines("gitwildmatch", adjusted)
        except FileNotFoundError:
            continue
    return spec

app = FastAPI()
current_dir = Path(__file__).parent
static_dir = current_dir / "static"
static_dir.mkdir(exist_ok=True)  # Create static directory if it doesn't exist
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(current_dir / "templates"))

def get_project_structure(base_path: Path):
    # Find git root and parse gitignore if in a git repository
    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    
    def build_tree(path: Path, root: Path):
        # Check if path should be ignored
        if git_root and path.is_relative_to(git_root):
            relative_to_git = path.relative_to(git_root)
            if ignore_spec and ignore_spec.match_file(relative_to_git):
                return None

        entry = {
            "path": str(path.relative_to(root)),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "children": []
        }
        if path.is_dir():
            children = []
            for child in path.iterdir():
                # Skip hidden files/dirs and git ignored paths
                if child.name.startswith("."):
                    continue
                if git_root and child.is_relative_to(git_root):
                    child_rel = child.relative_to(git_root)
                    if ignore_spec and ignore_spec.match_file(child_rel):
                        continue
                children.append(child)
            
            # Sort directories first then files, both alphabetically
            for child in sorted(children, key=lambda x: (x.is_file(), x.name.lower())):
                child_entry = build_tree(child, root)
                if child_entry:
                    entry["children"].append(child_entry)
        return entry
    
    # Start with a root entry that contains all top-level items
    root_entry = {
        "path": "",
        "name": base_path.name,
        "type": "directory",
        "children": []
    }
    # Add children to the root entry
    children = []
    for child in base_path.iterdir():
        # Skip hidden files/dirs and git ignored paths
        if child.name.startswith("."):
            continue
        if git_root and child.is_relative_to(git_root):
            child_rel = child.relative_to(git_root)
            if ignore_spec and ignore_spec.match_file(child_rel):
                continue
        children.append(child)
    
    for child in sorted(children, key=lambda x: (x.is_file(), x.name.lower())):
        child_entry = build_tree(child, base_path)
        if child_entry:
            root_entry["children"].append(child_entry)
    
    return root_entry

def process_files(selected_paths: list, base_path: Path):
    output = []
    for path in selected_paths:
        full_path = base_path / path
        if full_path.is_dir():
            for file_path in full_path.rglob("*"):
                if file_path.is_file():
                    process_file(file_path, base_path, output)
        else:
            process_file(full_path, base_path, output)
    return "\n".join(output)

def process_file(file_path: Path, base_path: Path, output: list):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            relative_path = file_path.relative_to(base_path)
            output.append(f"# File: {relative_path}\n{content}\n\n")
    except UnicodeDecodeError:
        pass

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    base_path = Path.cwd()
    structure = get_project_structure(base_path)
    return templates.TemplateResponse("index.html", {"request": request, "structure": structure})

@app.post("/process/")
async def process_files_route(selected_paths: list = Form(...)):
    base_path = Path.cwd()
    processed_content = process_files(selected_paths, base_path)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"llm_input_{timestamp}.txt"
    output_path = base_path / "outputs" / output_filename
    
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(processed_content)
    
    return FileResponse(output_path, filename=output_filename)
