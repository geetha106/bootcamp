from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import uvicorn
from pathlib import Path

from api.routes import router
from utils.logging import get_logger

# Create FastAPI app
app = FastAPI(
    title="FigureX API",
    description="API for extracting figure captions and metadata from scientific papers",
    version="1.0.0",
)

logger = get_logger("api.main")

# Create templates directory if it doesn't exist
templates_dir = Path("api/templates")
templates_dir.mkdir(exist_ok=True, parents=True)

# Create static directory if it doesn't exist
static_dir = Path("api/static")
static_dir.mkdir(exist_ok=True, parents=True)

# Mount static files
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="api/templates")

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 