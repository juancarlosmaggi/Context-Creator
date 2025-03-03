# Context Creator

Context Creator is a tool that generates a structured text file from selected files and directories within your project. Built with FastAPI, it offers a simple web interface to browse your project structure, select files or directories, and download their contents in a neatly formatted text file. This is particularly useful for creating context for large language models (LLMs), sharing code snippets, or documenting parts of your project.

## Installation

To get started with Context Creator, follow these steps:

1. **Clone or Download the Repository**
   
   Obtain the code by cloning the repository or downloading it to your local machine.

2. **Navigate to the Project Directory**
   
   Open a terminal and change to the directory containing the project files:
   ```bash
   cd /path/to/context-creator
   ```

3. **Install the Package**
   
   Use pip to install the package in editable mode, making the context-creator command available system-wide:
   ```bash
   pip install -e .
   ```
   
   The `-e` flag allows you to modify the code without reinstalling, ideal for development. For a standard installation, use `pip install .` instead.

## Usage

Once installed, you can use Context Creator in any project directory:

1. **Navigate to Your Project Directory**
   
   Move to the directory you want to analyze:
   ```bash
   cd /path/to/your/project
   ```

2. **Run the Tool**
   
   Start the web server by executing:
   ```bash
   context-creator
   ```

3. **Access the Web Interface**
   
   Open your browser and go to http://localhost:8000. Here, you can:
   - Browse your project's file structure.
   - Select files and directories using checkboxes.
   - Click the "Process" button to generate and download a text file with the selected contents.
   
   Note: The server runs until you stop it with Ctrl+C. For large projects, a loading screen may appear briefly while the index is built.

## Options

Customize how Context Creator runs with these command-line options:

- `--host`: Set the host address (default: 127.0.0.1).
- `--port`: Set the port number (default: 8000).
- `--reload`: Enable auto-reload for development (useful during code changes).

Example:
```bash
context-creator --port 8080 --reload
```

This runs the server on port 8080 with auto-reload enabled.

## Dependencies

Context Creator relies on the following Python packages, which are installed automatically with `pip install -e .`:

- fastapi - For the web framework.
- uvicorn - For the ASGI server.
- jinja2 - For templating the web interface.
- python-multipart - For handling form data.
- pathspec - For parsing .gitignore files.

## License

Context Creator is released under the MIT License.