#!/usr/bin/env python3
"""
Startup script for MemeGPT FastAPI backend
"""
import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Run the FastAPI app
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Set to False in production
        log_level="info"
    )