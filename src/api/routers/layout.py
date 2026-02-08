"""
Layout API Router

Endpoints per a disseny i optimització de layouts
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np

from src.calculations.layout import LayoutGA, LayoutGrid, LayoutOptimizer, calculate_layout_metrics


router = APIRouter(prefix="/layout", tags=["Layout Design"])


class LayoutConfigRequest(BaseModel):
    """Configuració per crear layout"""
    n_turbines: int
    min_distance: float = 500
    min_x: float
    max_x: float
    min_y: float
    max_y: float


class GridRequest(BaseModel):
    """Request per layout en graella"""
    n_rows: int
    n_cols: int
    spacing_x: float
    spacing_y: float
    offset_x: float = 0
    offset_y: float = 0
    staggered: bool = False


class OptimizationRequest(BaseModel):
    """Request per optimització"""
    n_turbines: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    method: str = "ga"  # ga, grid, random


class TurbinePosition(BaseModel):
    x: float
    y: float


class LayoutResponse(BaseModel):
    """Response del layout"""
    name: str
    turbines: list[dict]
    n_turbines: int
    metrics: dict
    fitness: float


@router.post("/grid", response_model=LayoutResponse)
async def create_grid_layout(request: GridRequest):
    """Crea layout en graella"""
    try:
        if request.staggered:
            layout = LayoutGrid.create_staggered(
                n_rows=request.n_rows,
                n_cols=request.n_cols,
                spacing_x=request.spacing_x,
                spacing_y=request.spacing_y,
                offset_x=request.offset_x,
                offset_y=request.offset_y
            )
        else:
            layout = LayoutGrid.create(
                n_rows=request.n_rows,
                n_cols=request.n_cols,
                spacing_x=request.spacing_x,
                spacing_y=request.spacing_y,
                offset_x=request.offset_x,
                offset_y=request.offset_y
            )
        
        metrics = calculate_layout_metrics(layout)
        
        return LayoutResponse(
            name=layout.name,
            turbines=[{"x": x, "y": y} for x, y in layout.turbines],
            n_turbines=len(layout.turbines),
            metrics=metrics,
            fitness=layout.fitness
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=LayoutResponse)
async def optimize_layout(request: OptimizationRequest):
    """Optimitza layout amb mètode especificat"""
    try:
        if request.method == "ga":
            # Configuració simple
            config = LayoutConfig(
                n_turbines=request.n_turbines,
                min_x=request.min_x,
                max_x=request.max_x,
                min_y=request.min_y,
                max_y=request.max_y
            )
            
            # GA simple (sense wake model per ara)
            ga = LayoutGA(
                config=config,
                wind_rose=np.ones(12) / 12,
                wake_model=None,
                population_size=50,
                n_generations=100
            )
            
            layout = ga.optimize()
        
        elif request.method == "grid":
            layout = LayoutOptimizer.optimize_grid(
                n_turbines=request.n_turbines,
                area_width=request.max_x - request.min_x,
                area_height=request.max_y - request.min_y,
                wind_rose=np.ones(12) / 12,
                wake_model=None
            )
        
        elif request.method == "random":
            layout = LayoutOptimizer.random_search(
                n_turbines=request.n_turbines,
                area_bounds=(request.min_x, request.max_x, request.min_y, request.max_y),
                n_iterations=500
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Mètode desconegut: {request.method}")
        
        metrics = calculate_layout_metrics(layout)
        
        return LayoutResponse(
            name=layout.name,
            turbines=[{"x": x, "y": y} for x, y in layout.turbines],
            n_turbines=len(layout.turbines),
            metrics=metrics,
            fitness=layout.fitness
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def get_layout_metrics(turbines: list[TurbinePosition]):
    """Calcula mètriques d'un layout existent"""
    try:
        layout = Layout(
            name="custom",
            turbines=[(t.x, t.y) for t in turbines]
        )
        
        metrics = calculate_layout_metrics(layout)
        
        return {
            "n_turbines": len(turbines),
            "metrics": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
