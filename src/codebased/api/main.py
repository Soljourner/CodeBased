"""
Main FastAPI application for CodeBased.
"""

import logging
import time
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_config
from ..database.service import get_database_service
from ..database.schema import GraphSchema
from .endpoints import create_router

logger = logging.getLogger(__name__)


def create_app(config_path: str = ".codebased.yml") -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured FastAPI application
    """
    # Load configuration
    config = get_config(config_path)
    
    # Initialize database
    db_service = get_database_service(config.database.path)
    if not db_service.initialize():
        raise RuntimeError("Failed to initialize database")
    
    # Create and initialize schema
    schema = GraphSchema(db_service)
    if not schema.create_schema():
        raise RuntimeError("Failed to create database schema")
    
    # Create FastAPI app
    app = FastAPI(
        title="CodeBased API",
        description="A lightweight code graph generator and visualization tool",
        version="0.1.0",
        docs_url="/docs" if config.api.enable_docs else None,
        redoc_url="/redoc" if config.api.enable_docs else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log HTTP requests and responses."""
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # Add exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "path": str(request.url.path)
            }
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        try:
            db_health = db_service.health_check()
            
            return {
                "status": "healthy" if db_health["status"] == "healthy" else "degraded",
                "timestamp": time.time(),
                "database": db_health,
                "version": "0.1.0"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e),
                "version": "0.1.0"
            }
    
    # Add API routes
    api_router = create_router(config, db_service)
    app.include_router(api_router, prefix="/api")
    
    # Serve static files (web frontend)
    try:
        app.mount("/", StaticFiles(directory=config.web.static_path, html=True), name="static")
    except RuntimeError:
        logger.warning(f"Static files directory not found: {config.web.static_path}")
    
    # Store config and services in app state
    app.state.config = config
    app.state.db_service = db_service
    app.state.schema = schema
    
    logger.info("FastAPI application created successfully")
    return app


# Create default app instance
app = create_app()