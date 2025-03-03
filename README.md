# Context Creator

A FastAPI application for creating context from files and directories.

## Installation

Install the package locally:

```
cd /path/to/create_context
pip install -e .
```

This will create a command-line tool called `context-creator` that you can use from anywhere.

## Usage

Navigate to any directory where you want to run the application and execute:

```
context-creator
```

Options:
- `--host`: Specify host address (default: 127.0.0.1)
- `--port`: Specify port number (default: 8000)
- `--reload`: Enable auto-reload for development

Example:
```
context-creator --port 8080 --reload
```

The application will be available at http://localhost:8000 (or your specified port)

## Dependencies

- fastapi
- uvicorn
- jinja2
- python-multipart
- pathspec