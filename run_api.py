#!/usr/bin/env python3
"""Script to run the FastAPI application."""
import sys
import os

# Add src directory to Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

if __name__ == "__main__":
  import uvicorn

  # reload=True spawns a subprocess watcher; in Docker the lifespan runs in
  # the subprocess which can be killed before completion. Disable for production.
  reload = os.environ.get("UVICORN_RELOAD", "false").lower() == "true"

  uvicorn.run(
    "api.app:app",
    host="0.0.0.0",
    port=8000,
    reload=reload,
    log_level="info"
  )
