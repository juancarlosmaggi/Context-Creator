# Context Creator

Context Creator is a user-friendly tool designed to generate a single, structured text output containing the contents of selected files and directories from your project. This is particularly useful for creating context for large language models (LLMs), sharing code snippets, or documenting specific parts of your codebase.

Built with **FastAPI**, it offers an intuitive web interface to browse your project's file structure, select items using checkboxes, filter files by name or regex, expand/collapse directories, and process selections. The tool respects `.gitignore` and `.contextignore` rules, skips hidden files (those starting with `.`), large files (>10MB), and unreadable files. The output is formatted with clear delimiters (e.g., `----- BEGIN FILE: relative/path -----` and `----- END FILE -----`) and copied directly to your clipboard for seamless use.

## Features

- **Interactive Web UI**: Browse and select files/directories with checkboxes, filters, and expand/collapse functionality.
- **Folder Filter Action**: Hover over folders to reveal an action button that sets a regex filter to show only files within that folder and its subfolders.
- **gitignore Support**: Automatically ignores files and directories specified in `.gitignore` files.
- **contextignore Support**: Ignores files and directories listed in `.contextignore` at the project root (same syntax as `.gitignore`).
- **Efficient Indexing**: Builds a project index on startup with a loading screen for large projects, cached in memory for 24 hours.
- **Customization**: Command-line options for host, port, and auto-reload during development.
- **Clipboard Integration**: Processed content is copied to your clipboard for easy pasting into LLMs or other tools.
- **Parallel Processing**: Uses threading for faster handling of large directories and file reading.

## Installation

Choose one of the following methods to install Context Creator:

### Option 1: Install Directly via pip (Recommended)

Install globally using pip directly from the GitHub repository to make the `context-creator` command available system-wide:

```bash
pip install git+https://github.com/juancarlosmaggi/Context-Creator.git
```

### Option 2: Clone and Install for Development

For modifying the code or contributing:

1. Clone the repository:

   ```bash
   git clone https://github.com/juancarlosmaggi/Context-Creator.git
   cd Context-Creator
   ```

2. Install in editable mode (changes take effect without reinstalling):

   ```bash
   pip install -e .
   ```

   Alternatively, for a standard installation, use `pip install .`.

## Usage

Context Creator operates in your project's current working directory.

1. **Navigate to Your Project Directory**:

   ```bash
   cd /path/to/your/project
   ```

2. **Run the Tool**:

   Start the FastAPI server:

   ```bash
   context-creator
   ```

   This launches the server at `http://127.0.0.1:8000` (default).

3. **Access the Web Interface**:

   Open your browser to `http://127.0.0.1:8000`.

   - A loading screen appears during index building for large projects.
   - The interface displays your project structure (e.g., "Project Explorer - MyProject").
   - Filter files by name or regex (toggle "Use Regex"; simple search highlights matches in filenames, regex matches against the full relative path with forward slashes, e.g., `^templates/.*` to show all files in the templates folder and subfolders).
   - Hover over folders to show an action button for quick filtering to that directory.
   - Expand/collapse directories using buttons or "Expand All"/"Collapse All".
   - Select files or directories with checkboxes (directory selection includes all files recursively).
   - A floating "Process" button shows the number of selected files and activates when selections are made.
   - Click "Process" to generate and copy the formatted text to your clipboard with a confirmation alert.

   Stop the server with `Ctrl+C` in the terminal.

## Command-Line Options

Customize the server with these options (defaults shown):

- `--host`: Host address (default: `127.0.0.1`). Use `0.0.0.0` for external access.
- `--port`: Port number (default: `8000`).
- `--reload`: Enable auto-reload for development (default: disabled).

Example:

```bash
context-creator --host 0.0.0.0 --port 8080 --reload
```

This runs the server on port 8080, accessible from any IP, with auto-reload enabled.

## How It Works

- **Indexing**: On startup, scans your project to build a tree structure, respecting `.gitignore` and `.contextignore`, and skips hidden items. Uses parallel processing for speed.
- **Selection**: Lists directories and files sorted alphabetically (directories first).
- **Processing**: Reads selected items in parallel, formats them with clear delimiters, and copies the output to your clipboard.
- **Limitations**: Skips files >10MB or unreadable. Binary files may not display correctly (treated as text).

For large projects, the initial index build may take a few seconds—please be patient!

## Dependencies

Installed automatically during setup:

- `fastapi`: Web framework.
- `uvicorn`: ASGI server.
- `jinja2`: Templating.
- `python-multipart`: Form handling.
- `pathspec`: `.gitignore` parsing.

## License

Released under the MIT License. See the [LICENSE](LICENSE) file for details.