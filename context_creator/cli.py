import uvicorn
import argparse

def main():
    parser = argparse.ArgumentParser(description="Context Creator")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    # Run uvicorn with the properly qualified module path
    uvicorn.run(
        "context_creator.main:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload,
        factory=False
    )

if __name__ == "__main__":
    main()
