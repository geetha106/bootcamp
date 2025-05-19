from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
import os
import uvicorn
from pathlib import Path
from typing import Optional

from api.routes import router
from api.auth import get_api_key, get_api_key_optional
from utils.logging import get_logger
from config.config import get_config

# Get configuration
config = get_config()
api_key = config.api.api_key
api_docs_enabled = True  # Can be moved to settings.yaml if needed

# Create FastAPI app
app = FastAPI(
    title="FigureX API",
    description="API for extracting figure captions and metadata from scientific papers",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
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


# Custom API documentation with API key authentication
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(
    api_key: Optional[str] = Depends(get_api_key_optional)
):
    """Custom Swagger UI with API key authentication"""
    if not api_docs_enabled:
        return {"message": "API documentation is disabled"}
    
    return get_swagger_ui_html(
        openapi_url=f"/openapi.json?api_key={api_key}" if api_key else "/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html(
    api_key: Optional[str] = Depends(get_api_key_optional)
):
    """Custom ReDoc with API key authentication"""
    if not api_docs_enabled:
        return {"message": "API documentation is disabled"}
    
    return get_redoc_html(
        openapi_url=f"/openapi.json?api_key={api_key}" if api_key else "/openapi.json",
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint(
    api_key: Optional[str] = Depends(get_api_key_optional)
):
    """Get OpenAPI schema with API key authentication"""
    if not api_docs_enabled:
        return {"message": "API documentation is disabled"}
    
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


if __name__ == "__main__":
    if api_key == "changeme123":
        logger.warning("Using default API key. Consider setting a secure API key in settings.yaml")
    
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 