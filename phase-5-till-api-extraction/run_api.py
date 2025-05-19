#!/usr/bin/env python3
"""
Run the FigureX API server
"""
import uvicorn
import os
from pathlib import Path

# Create necessary directories if they don't exist
os.makedirs("api/templates", exist_ok=True)
os.makedirs("api/static/css", exist_ok=True)
os.makedirs("api/static/js", exist_ok=True)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

if __name__ == "__main__":
    print("Starting FigureX API server...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 