#!/usr/bin/env python3
"""Backend development server entry point."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
