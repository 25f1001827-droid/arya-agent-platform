import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.database import create_tables, engine
from app.routes import auth, pages, content, analytics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting up Social Media Automation Platform...")

    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

    # Additional startup tasks
    logger.info(f"Application started in {settings.ENVIRONMENT} environment")
    logger.info(f"Region: {settings.REGION}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["yourdomain.com", "*.yourdomain.com"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    """Add processing time header to responses."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """Log all incoming requests."""
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "request_id": str(id(request))
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "region": settings.REGION,
        "version": settings.VERSION,
        "timestamp": time.time()
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Social Media Automation Platform API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "region": settings.REGION,
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_check": "/health"
    }


# Include API routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    pages.router,
    prefix="/api/v1/pages",
    tags=["Facebook Pages"]
)

app.include_router(
    content.router,
    prefix="/api/v1/content",
    tags=["Content Generation"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)


# Rate limiting endpoint for monitoring
@app.get("/api/v1/status", tags=["Status"])
async def get_api_status():
    """Get API status and metrics."""
    return {
        "status": "operational",
        "region": settings.REGION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "ai_content_generation": True,
            "facebook_integration": True,
            "automated_scheduling": True,
            "analytics_collection": True,
            "optimization_engine": True
        },
        "limits": {
            "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "rate_limit_per_hour": settings.RATE_LIMIT_PER_HOUR
        }
    }


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
