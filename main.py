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
    patterns = []
    
    # First process the root .gitignore
    root_gitignore = git_root / ".gitignore"
    if root_gitignore.exists():
        try:
            with open(root_gitignore, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                patterns.extend(lines)
        except FileNotFoundError:
            pass
    
    # Then process all other .gitignore files
    for gitignore_path in git_root.glob("*/**/.gitignore"):  # Skip root .gitignore we processed above
        relative_dir = gitignore_path.parent.relative_to(git_root)
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                # For patterns that don't start with '/', prefix with the directory path
                adjusted = []
                for line in lines:
                    if line.startswith('/'):
                        # This is a directory-specific absolute pattern, make it relative to this directory
                        adjusted.append(str(relative_dir / line[1:]))
                    else:
                        # This is already a pattern relative to the .gitignore location
                        adjusted.append(str(relative_dir / line))
                patterns.extend(adjusted)
        except FileNotFoundError:
            continue

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

def should_ignore(path: Path, git_root: Path, ignore_spec: pathspec.PathSpec) -> bool:
    """Determine if a path should be ignored based on .gitignore rules."""
    # Always ignore hidden files/dirs
    if path.name.startswith("."):
        return True
    
    # Check against gitignore patterns
    if git_root and path.is_relative_to(git_root):
        rel_path = path.relative_to(git_root)
        # Check both the path and the path with trailing slash for directories
        if ignore_spec.match_file(rel_path):
            return True
        if path.is_dir() and ignore_spec.match_file(str(rel_path) + '/'):
            return True
    
    return False

# Add a debugging function to test gitignore patterns
@app.get("/api/test-gitignore/{path:path}")
async def test_gitignore(path: str):
    """Test if a specific path would be ignored by gitignore rules."""
    base_path = Path.cwd()
    git_root = find_git_root(base_path)
    if not git_root:
        return {"error": "No git repository found"}
    
    ignore_spec = parse_gitignore(git_root)
    test_path = Path(path)
    full_path = base_path / test_path
    
    result = {
        "path": path,
        "is_ignored": should_ignore(full_path, git_root, ignore_spec),
        "exists": full_path.exists(),
        "is_dir": full_path.is_dir() if full_path.exists() else None,
    }
    
    # Show which patterns would match this path
    if full_path.is_relative_to(git_root):
        rel_path = full_path.relative_to(git_root)
        pattern_matches = []
        for pattern in ignore_spec.patterns:
            if pattern.match_file(rel_path) or pattern.match_file(str(rel_path) + '/'):
                pattern_matches.append(str(pattern))
        result["matching_patterns"] = pattern_matches
    
    return result

# Update the get_project_structure function to use our improved should_ignore function
@functools.lru_cache(maxsize=32)
def get_project_structure(base_path: Path):
    """Build the project structure tree, respecting .gitignore rules."""
    git_root = find_git_root(base_path)
    ignore_spec = parse_gitignore(git_root) if git_root else None
    
    def build_tree(path: Path, root: Path):
        if ignore_spec and should_ignore(path, git_root, ignore_spec):
            return None
        
        entry = {
            "path": str(path.relative_to(root)),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "children": []
        }
        
        if path.is_dir():
            try:
                children = []
                for child in path.iterdir():
                    if ignore_spec and should_ignore(child, git_root, ignore_spec):
                        continue
                    children.append(child)
                
                # Sort directories first, then files, both alphabetically
                children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
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
    
    # Continue with the rest of the function as before
    root_entry = {
        "path": "",
        "name": base_path.name,
        "type": "directory",
        "children": []
    }
    
    try:
        children = []
        for child in base_path.iterdir():
            if ignore_spec and should_ignore(child, git_root, ignore_spec):
                continue
            children.append(child)
            
        # Sort directories first, then files, both alphabetically
        children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
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

def is_index_valid(max_age_hours=24) -> bool:
    """Check if the index file exists and is recent enough."""
    index_path = Path(INDEX_FILE)
    if not index_path.exists():
        return False
        
    # Check if the index is recent enough
    try:
        mtime = datetime.fromtimestamp(index_path.stat().st_mtime)
        age = datetime.now() - mtime
        if age.total_seconds() > max_age_hours * 3600:
            return False
            
        # Verify the index file is valid JSON
        with open(index_path, 'r') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False

async def get_or_build_index(base_path: Path, background_tasks: BackgroundTasks):
    """Get the cached index or trigger a rebuild if necessary."""
    index_status = IndexStatus()
    
    # If index is already valid, don't rebuild
    if index_status.is_valid or is_index_valid():
        index_status.is_valid = True
        return None
        
    # If not already building, start the build process
    if not index_status.is_building:
        index_status.is_building = True
        background_tasks.add_task(build_and_save_index, base_path)
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, background_tasks: BackgroundTasks):
    """Serve the index page, triggering index build if necessary."""
    base_path = Path.cwd()
    index_status = IndexStatus()
    
    # If index is valid or can be validated, serve the main page
    if index_status.is_valid or is_index_valid():
        index_status.is_valid = True
        return templates.TemplateResponse("index.html", {"request": request})
    
    # Otherwise, trigger a build and show the loading page
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