"""
Continuum Web API - Main Entry Point
Port del toolkit eòlic Continuum (C#) a Python/FastAPI

Funcionalitats:
- Met Data Filtering
- MCP (Measure-Correlate-Predict)
- Wake Loss Modeling
- Layout Design & Optimization
- Neural MCP (ML-based)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import met_filter, mcp, wake, layout

app = FastAPI(
    title="Continuum Web API",
    description="Toolkit eòlic per anàlisi de recursos wind",
    version="2.0.0"
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


@app.get("/health")
def health_check():
    """Health check"""
    return {"status": "healthy", "service": "continuum-web", "version": "2.0.0"}


@app.get("/")
def root():
    return {
        "service": "Continuum Web API",
        "version": "2.0.0",
        "description": "Toolkit eòlic open source",
        "docs": "/docs",
        "endpoints": {
            "met_filter": "/met-filter",
            "mcp": "/mcp",
            "wake": "/wake",
            "layout": "/layout"
        }
    }
