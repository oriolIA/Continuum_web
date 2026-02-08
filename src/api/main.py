"""
Continuum Web API - Working Version
Full implementation with all features
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.api.routers import met_filter, mcp, wake, layout, projects, files

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Continuum Web API",
    description="Wind Resource Toolkit - Full Implementation",
    version="2.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Include routers
app.include_router(met_filter.router)
app.include_router(mcp.router)
app.include_router(wake.router)
app.include_router(layout.router)
app.include_router(projects.router)
app.include_router(files.router)


@app.get("/")
def root():
    """Serve the main HTML page"""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "Continuum Web API",
        "version": "2.1.0",
        "docs": "/docs",
        "frontend": "Not found - check frontend directory"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "continuum-web", "version": "2.1.0"}
