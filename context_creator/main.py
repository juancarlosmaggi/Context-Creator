from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
from typing import List

from context_creator.core.ignore import (
    find_git_root,
    parse_gitignore,
    parse_contextignore,
    should_ignore
)
from context_creator.core.index import (
    IndexStatus,
    get_project_structure,
    build_and_save_index,
    get_or_build_index
)
from context_creator.core.processor import process_files

app = FastAPI(title="Context Creator")

current_dir = Path(__file__).parent
static_dir = current_dir / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(current_dir / "templates"))

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

# Add a debugging function to test gitignore patterns
@app.get("/api/test-gitignore/{path:path}")
async def test_gitignore(path: str):
    """Test if a specific path would be ignored by gitignore rules."""
    base_path = Path.cwd()
    git_root = find_git_root(base_path)
    if not git_root:
        return {"error": "No git repository found"}
    ignore_spec = parse_gitignore(git_root)
    context_ignore_spec = parse_contextignore(base_path)

    test_path = Path(path)
    full_path = base_path / test_path

    result = {
        "path": path,
        "is_ignored": should_ignore(full_path, base_path, git_root, ignore_spec, context_ignore_spec),
        "exists": full_path.exists(),
        "is_dir": full_path.is_dir() if full_path.exists() else None,
    }

    # Show which patterns would match this path from gitignore
    git_pattern_matches = []
    if git_root and full_path.is_relative_to(git_root):
        rel_path = full_path.relative_to(git_root)
        if ignore_spec:
            for pattern in ignore_spec.patterns:
                if pattern.match_file(rel_path) or pattern.match_file(str(rel_path) + '/'):
                    git_pattern_matches.append(str(pattern))
    result["git_matching_patterns"] = git_pattern_matches

    # Show which patterns would match this path from contextignore
    context_pattern_matches = []
    if full_path.is_relative_to(base_path):
        rel_path = full_path.relative_to(base_path)
        if context_ignore_spec:
            for pattern in context_ignore_spec.patterns:
                if pattern.match_file(rel_path) or pattern.match_file(str(rel_path) + '/'):
                    context_pattern_matches.append(str(pattern))
    result["context_matching_patterns"] = context_pattern_matches

    return result

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, background_tasks: BackgroundTasks):
    """Serve the index page, triggering index build if necessary."""
    base_path = Path.cwd()
    index_status = IndexStatus()

    # If index is valid and recent enough, serve the main page
    if index_status.is_valid and index_status.created_at:
        age = datetime.now() - index_status.created_at
        if age.total_seconds() <= 24 * 3600:
            return templates.TemplateResponse(request=request, name="index.html")

    # Otherwise, trigger a build and show the loading page
    await get_or_build_index(base_path, background_tasks)
    return templates.TemplateResponse(request=request, name="loading.html")

@app.get("/api/index-status")
async def get_index_status_route():
    """Return the current index status."""
    status = IndexStatus()
    return {"is_valid": status.is_valid, "is_building": status.is_building}

@app.post("/process/")
async def process_files_route(selected_paths: List[str] = Form(...)):
    """Process selected paths and return the output as text."""
    base_path = Path.cwd()
    processed_content = await run_in_threadpool(process_files, selected_paths, base_path)
    return Response(content=processed_content, media_type="text/plain")

@app.get("/api/project-structure")
async def get_project_structure_json():
    """Serve the in-memory project structure."""
    index_status = IndexStatus()
    if not index_status.structure:
        return JSONResponse(content={"error": "Index is not built yet"}, status_code=503)
    return JSONResponse(content=index_status.structure)

@app.post("/api/rebuild-index")
async def rebuild_index(background_tasks: BackgroundTasks):
    """Force a rebuild of the project index."""
    base_path = Path.cwd()
    index_status = IndexStatus()
    index_status.is_building = True
    index_status.is_valid = False

    # Clear the lru_cache for get_project_structure
    get_project_structure.cache_clear()

    background_tasks.add_task(build_and_save_index, base_path)
    return {"status": "rebuilding"}
