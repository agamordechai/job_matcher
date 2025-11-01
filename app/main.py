"""Main FastAPI application"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
from app.config import get_settings
from app.database import init_db
from app.routers import cv, jobs, filters, scheduler, system

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Job Matcher application...")
    init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down Job Matcher application...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Job Matching Microservice System",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.environment == "development" else "An error occurred",
        },
    )


# Include routers
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(cv.router, prefix="/api/cv", tags=["CV Management"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Job Management"])
app.include_router(filters.router, prefix="/api/filters", tags=["Search Filters"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat(),
    }

