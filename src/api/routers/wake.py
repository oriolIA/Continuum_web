"""
Wake API Router

Endpoints per a modelat de pèrdues de wake
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import list
import numpy as np

from src.calculations.wake import WakeCollection, WakeModelConfig, calculate_wake_losses


router = APIRouter(prefix="/wake", tags=["Wake Loss Modeling"])


class TurbineInput(BaseModel):
    name: str
    x: float
    y: float
    hub_height: float
    rotor_diameter: float
    ct: float = 0.8


class WakeRequest(BaseModel):
    turbines: list[TurbineInput]
    grid_resolution: int = 50
    sectors: int = 12


class SectorLoss(BaseModel):
    sector: int
    direction_range: tuple[float, float]
    wake_loss_percent: float


class WakeResponse(BaseModel):
    global_wake_loss_percent: float
    sector_losses: list[SectorLoss]
    n_turbines: int
    grid_shape: tuple


@router.post("/calculate", response_model=WakeResponse)
async def calculate_wake(request: WakeRequest):
    """Calcula pèrdues de wake del parc eòlic"""
    try:
        result = calculate_wake_losses(
            turbines=request.turbines,
            wind_data=None,  # Opcional
            grid_resolution=request.grid_resolution
        )
        
        return WakeResponse(
            global_wake_loss_percent=result['global_wake_loss_percent'],
            sector_losses=[
                SectorLoss(
                    sector=int(s.split('_')[1]),
                    direction_range=v['direction_range'],
                    wake_loss_percent=v['wake_loss_percent']
                )
                for s, v in result['sector_losses'].items()
            ],
            n_turbines=result['n_turbines'],
            grid_shape=(request.grid_resolution, request.grid_resolution)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
