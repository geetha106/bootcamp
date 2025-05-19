from fastapi import Security, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from typing import Optional
import os
from dotenv import load_dotenv
from utils.logging import get_logger

logger = get_logger("api.auth")

# Load environment variables from .env file if it exists
load_dotenv()

# Get API key from environment variable or use a default for development
API_KEY = os.getenv("API_KEY", "figurex_default_key")
API_KEY_NAME = "api-key"

# Define API key security schemes
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)


async def get_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
):
    """
    Verify API key from header or query parameter.
    
    This function can be used as a dependency in FastAPI routes to enforce API key authentication.
    """
    if api_key_header == API_KEY:
        return api_key_header
    elif api_key_query == API_KEY:
        return api_key_query
    else:
        logger.warning(f"Invalid API key attempt: {api_key_header or api_key_query or 'None provided'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        ) 