from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from config.config import get_config
from utils.logging import get_logger
from typing import Optional

logger = get_logger("api.auth")

# Configuration
config = get_config()
API_KEY = config.api.api_key
API_KEY_NAME = "X-API-Key"
API_KEY_QUERY = "api_key"

# Security schemes
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name=API_KEY_QUERY, auto_error=False)


async def get_api_key(
    request: Request,
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> str:
    """
    Get API key from header or query parameter.
    
    Args:
        request: The FastAPI request object
        api_key_header: API key from header
        api_key_query: API key from query parameter
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Log all headers for debugging
    logger.debug(f"All headers: {request.headers}")
    logger.debug(f"API key header: {api_key_header}, API key query: {api_key_query}")
    
    # Try to get API key from header first
    header_key = request.headers.get(API_KEY_NAME)
    if header_key:
        logger.debug(f"Found API key in raw headers: {header_key}")
        return validate_api_key(header_key)
    
    # Then from FastAPI's extracted header
    if api_key_header:
        logger.debug(f"Found API key in FastAPI header: {api_key_header}")
        return validate_api_key(api_key_header)
    
    # Then from query parameter
    if api_key_query:
        logger.debug(f"Found API key in query: {api_key_query}")
        return validate_api_key(api_key_query)
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key is missing. Provide it in the X-API-Key header or api_key query parameter.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def validate_api_key(api_key: str) -> str:
    """
    Validate API key.
    
    Args:
        api_key: API key to validate
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    logger.debug(f"Validating API key: {api_key}")
    logger.debug(f"Expected API key: {API_KEY}")
    
    if api_key == API_KEY:
        return api_key
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def get_api_key_optional(
    request: Request,
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[str]:
    """
    Get API key from header or query parameter, but don't require it.
    
    Args:
        request: The FastAPI request object
        api_key_header: API key from header
        api_key_query: API key from query parameter
        
    Returns:
        The API key if valid, None otherwise
    """
    # Try to get API key from header first
    header_key = request.headers.get(API_KEY_NAME)
    if header_key:
        try:
            return validate_api_key(header_key)
        except HTTPException:
            return None
    
    # Then from FastAPI's extracted header
    if api_key_header:
        try:
            return validate_api_key(api_key_header)
        except HTTPException:
            return None
    
    # Then from query parameter
    if api_key_query:
        try:
            return validate_api_key(api_key_query)
        except HTTPException:
            return None
            
    return None 