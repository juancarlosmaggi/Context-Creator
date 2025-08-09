# Context Creator
Context Creator is a user-friendly tool that helps you generate a single, structured text file containing the contents of selected files and directories from your project. This is especially helpful for creating context for large language models (LLMs), sharing code snippets, or documenting specific parts of your codebase.
Built with FastAPI, it provides an intuitive web interface where you can browse your project's file structure, select items using checkboxes, filter files by name, expand/collapse directories, and process your selections. The tool automatically respects `.gitignore` and `.contextignore` rules and skips hidden files (those starting with `.`), large files (>10MB), and files it can't read.
When you process your selections, the generated text is copied directly to your clipboard in a formatted structure (e.g., `# File: relative/path\ncontent\n\n`). No downloads are involved—it's quick and seamless!
## Features
- **Interactive Web UI**: Browse and select files/directories with checkboxes, filters, and expand/collapse functionality.
- **gitignore Support**: Automatically ignores files and directories specified in your project's `.gitignore` files.
- **contextignore Support**: Additionally ignores files and directories specified in `.contextignore` at the project root (using the same syntax as .gitignore).
- **Efficient Indexing**: Builds a project index on startup (with a loading screen for large projects) and caches it in memory for 24 hours.
- **Customization**: Command-line options for host, port, and auto-reload during development.
- **Clipboard Integration**: Processed content is copied to your clipboard for easy pasting into LLMs or other tools.
- **Parallel Processing**: Uses threading for faster handling of large directories and file reading.
## Installation
You have two options for installation: directly from GitHub (easiest for users) or by cloning the repository (recommended for developers).
### Option 1: Install Directly via pip (Recommended)
Install the package globally using pip directly from the GitHub repository. This makes the `context-creator` command available system-wide without cloning.
```bash
pip install git+https://github.com/juancarlosmaggi/Context-Creator.git
```
### Option 2: Clone and Install for Development
If you want to modify the code or contribute:
1. Clone the repository:
   ```bash
   git clone https://github.com/juancarlosmaggi/Context-Creator.git
   cd Context-Creator
   ```
2. Install in editable mode (changes take effect without reinstalling):
   ```bash
   pip install -e .
   ```
   For a standard installation, use `pip install .` instead.
## Usage
Context Creator runs in the current working directory (your project folder). It analyzes files from there.
1. **Navigate to Your Project Directory**
   ```bash
   cd /path/to/your/project
   ```
2. **Run the Tool**
   Start the FastAPI server:
   ```bash
   context-creator
   ```
   This launches the server on http://127.0.0.1:8000 (default).
3. **Access the Web Interface**
   Open your browser to http://127.0.0.1:8000.
   - If the project index is building (for large projects), you'll see a loading screen.
   - Once loaded, you'll see your project structure (named after your folder, e.g., "Project Explorer - MyProject").
   - Use the filter input to search for files by name (highlights matches).
   - Expand/collapse directories with buttons or the "Expand All"/"Collapse All" options.
   - Select files or directories using checkboxes (selecting a directory selects all its files recursively).
   - A floating button shows the number of selected files and becomes active when selections are made.
   - Click the floating "Process" button to generate the text and copy it to your clipboard (with a confirmation alert).
   Stop the server with Ctrl+C in the terminal.
## Command-Line Options
Customize the server with these options (defaults shown):
- `--host`: Host address (default: 127.0.0.1). Use 0.0.0.0 to allow access from other machines.
- `--port`: Port number (default: 8000).
- `--reload`: Enable auto-reload for development (default: disabled). Automatically restarts the server on code changes.
Example:
```bash
context-creator --host 0.0.0.0 --port 8080 --reload
```
This runs the server on port 8080, accessible from any IP, with auto-reload enabled.
## How It Works
- **Indexing**: On startup, the tool scans your project, building a tree structure while respecting `.gitignore` and `.contextignore` and skipping hidden items. This is done in parallel for speed.
- **Selection**: Directories and files are listed sorted (directories first, then files alphabetically).
- **Processing**: Selected items are read in parallel, formatted, and returned as text. The frontend copies this to your clipboard.
- **Limitations**: Skips files >10MB or unreadable. Binary files may not display properly (treated as text).
For very large projects, the initial index build may take a few seconds—be patient!
## Dependencies
Installed automatically during setup:
- `fastapi`: Web framework.
- `uvicorn`: ASGI server.
- `jinja2`: Templating.
- `python-multipart`: Form handling.
- `pathspec`: `.gitignore` parsing.
## License
Released under the MIT License. See the [LICENSE](LICENSE) file for details (or add one if missing).