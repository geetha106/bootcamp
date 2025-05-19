#!/usr/bin/env python3
"""
Run the FigureX API server
"""
import uvicorn
import os
import yaml
from pathlib import Path

# Create necessary directories if they don't exist
os.makedirs("api/templates", exist_ok=True)
os.makedirs("api/static/css", exist_ok=True)
os.makedirs("api/static/js", exist_ok=True)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Get API key from settings.yaml
try:
    with open("settings.yaml", "r") as f:
        settings = yaml.safe_load(f)
        api_key = settings.get("api", {}).get("api_key", "changeme123")
        print(f"Using API key from settings.yaml: {api_key}")
        print("You'll need this key to access the API.")
        print("To change the API key, edit the 'api_key' field in settings.yaml")
except Exception as e:
    print(f"Error loading settings: {e}")
    api_key = "changeme123"
    print(f"Using default API key: {api_key}")

if __name__ == "__main__":
    print("Starting FigureX API server...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 