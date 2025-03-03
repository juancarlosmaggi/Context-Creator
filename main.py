from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
import os
import json
from pathlib import Path
from datetime import datetime
import pathspec
import functools
import concurrent.futures

app = FastAPI()
current_dir = Path(__file__).parent
static_dir = current_dir / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(current_dir / "templates"))

INDEX_FILE = ".cache/project_index.json"
CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

class IndexStatus:
    _instance = None
    is_building = False
    is_valid = False
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

def find_git_root(path: Path) -> Path | None:
    """Find the nearest parent directory containing a .git folder."""
    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent
    return None

def parse_gitignore(git_root: Path) -> pathspec.PathSpec:
    """Parse all .gitignore files in the repository into a PathSpec."""
    spec = pathspec.PathSpec([])
    for gitignore_path in git_root.glob("**/.gitignore"):
        relative_dir = gitignore_path.parent.relative_to(git_root)
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                adjusted = [str(relative_dir / line) if relative_dir != Path('.') else line 
                            for line in lines]
                spec += pathspec.PathSpec.from_lines("gitwildmatch", adjusted)
        except FileNotFoundError:
            continue
    return spec

@functools.lru_cache(maxsize=32)
def get_project_structure(base_path: Path):
    """Build the project structure tree, respecting .gitignore rules."""
    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    
    def should_ignore(path: Path) -> bool:
        if path.name.startswith("."):
            return True
        if git_root and path.is_relative_to(git_root):
            child_rel = path.relative_to(git_root)
            if ignore_spec and ignore_spec.match_file(child_rel):
                return True
        return False
    
    def build_tree(path: Path, root: Path):
        if should_ignore(path):
            return None
        entry = {
            "path": str(path.relative_to(root)),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "children": []
        }
        
        if path.is_dir():
            try:
                children = [child for child in path.iterdir() if not should_ignore(child)]
                children.sort(key=lambda x: (x.is_file(), x.name.lower()))
                if len(children) > 20:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                        futures = {executor.submit(build_tree, child, root): child for child in children}
                        for future in concurrent.futures.as_completed(futures):
                            child_entry = future.result()
                            if child_entry:
                                entry["children"].append(child_entry)
                else:
                    for child in children:
                        child_entry = build_tree(child, root)
                        if child_entry:
                            entry["children"].append(child_entry)
            except (PermissionError, OSError):
                pass
                
        return entry
    
    root_entry = {
        "path": "",
        "name": base_path.name,
        "type": "directory",
        "children": []
    }
    
    try:
        children = [child for child in base_path.iterdir() if not should_ignore(child)]
        children.sort(key=lambda x: (x.is_file(), x.name.lower()))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(build_tree, child, base_path): child for child in children}
            for future in concurrent.futures.as_completed(futures):
                try:
                    child_entry = future.result()
                    if child_entry:
                        root_entry["children"].append(child_entry)
                except Exception:
                    continue
    except (PermissionError, OSError):
        pass
    
    return root_entry

def process_files(selected_paths: list, base_path: Path):
    """Process selected files and directories into a single text output."""
    output = []
    
    def process_file(file_path: Path):
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # Skip files > 10MB
                return f"# File: {file_path.relative_to(base_path)}\n# [File too large - {file_path.stat().st_size / 1024 / 1024:.2f} MB]\n\n"
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                relative_path = file_path.relative_to(base_path)
                return f"# File: {relative_path}\n{content}\n\n"
        except (UnicodeDecodeError, PermissionError, OSError):
            return f"# File: {file_path.relative_to(base_path)}\n# [Unable to process file]\n\n"
    
    all_files = []
    for path in selected_paths:
        full_path = base_path / path
        if full_path.is_dir():
            all_files.extend([f for f in full_path.rglob("*") if f.is_file()])
        elif full_path.is_file():
            all_files.append(full_path)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, os.cpu_count() * 4)) as executor:
        results = list(executor.map(process_file, all_files))
    
    return "".join(results)

async def build_and_save_index(base_path: Path):
    """Build and cache the project structure in the background."""
    index_status = IndexStatus()
    try:
        structure = await run_in_threadpool(get_project_structure, base_path)
        data = {"structure": structure, "created_at": datetime.now().isoformat()}
        with open(INDEX_FILE, 'w') as f:
            json.dump(data, f)
        index_status.is_valid = True
    finally:
        index_status.is_building = False

async def get_or_build_index(base_path: Path, background_tasks: BackgroundTasks):
    """Get the cached index or trigger a rebuild if necessary."""
    index_status = IndexStatus()
    if not index_status.is_building:
        index_status.is_building = True
        background_tasks.add_task(build_and_save_index, base_path)
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, background_tasks: BackgroundTasks):
    """Serve the index page, triggering index build if necessary."""
    base_path = Path.cwd()
    if IndexStatus().is_valid and Path(INDEX_FILE).exists():
        return templates.TemplateResponse("index.html", {"request": request})
    await get_or_build_index(base_path, background_tasks)
    return templates.TemplateResponse("loading.html", {"request": request})

@app.get("/api/index-status")
async def get_index_status():
    """Return the current index status."""
    status = IndexStatus()
    return {"is_valid": status.is_valid, "is_building": status.is_building}

@app.post("/process/", response_class=FileResponse)
async def process_files_route(selected_paths: list = Form(...)):
    """Process selected paths and return the output file."""
    base_path = Path.cwd()
    processed_content = process_files(selected_paths, base_path)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"llm_input_{timestamp}.txt"
    output_path = base_path / "outputs" / output_filename
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(processed_content)
    return FileResponse(output_path, filename=output_filename)

@app.get("/api/project-structure")
async def get_project_structure_json():
    """Serve the cached project structure JSON."""
    if not os.path.exists(INDEX_FILE):
        return JSONResponse(content={"error": "Index is not built yet"}, status_code=503)
    with open(INDEX_FILE, 'r') as f:
        data = json.load(f)
    return JSONResponse(content=data["structure"])