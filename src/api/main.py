"""
Continuum Web API - Working Version
Full implementation with all features
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api.routers import met_filter, mcp, wake, layout, projects, files

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

# Include routers
app.include_router(met_filter.router)
app.include_router(mcp.router)
app.include_router(wake.router)
app.include_router(layout.router)
app.include_router(projects.router)
app.include_router(files.router)


@app.get("/")
def root():
    return {
        "service": "Continuum Web API",
        "version": "2.1.0",
        "docs": "/docs",
        "endpoints": [
            "/projects/create",
            "/projects/list",
            "/projects/{name}",
            "/files/upload",
            "/files/list",
            "/met-filter/filter",
            "/mcp/analyze",
            "/wake/calculate",
            "/layout/grid",
            "/layout/optimize"
        ]
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "continuum-web", "version": "2.1.0"}
