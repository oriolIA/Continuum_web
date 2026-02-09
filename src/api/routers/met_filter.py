"""
Met Filter API Router

Endpoints per a filtratge de dades meteorològiques
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import io

from src.calculations.met_filter import filter_met_data, MetDataFilter


router = APIRouter(prefix="/met-filter", tags=["Met Data Filtering"])


class FilterRequest(BaseModel):
    """Request per filtratge de dades"""
    # Format: list of dicts (row-based)
    data: Optional[List[Dict[str, Any]]] = None
    # Format: columns (column-based) - alternative input
    timestamps: Optional[List[str]] = None
    wind_speed: Optional[List[float]] = None
    wind_direction: Optional[List[float]] = None
    temperature: Optional[List[float]] = None
    # Options
    remove_tower_shadow: bool = True
    remove_ice: bool = True
    remove_high_std: bool = True
    ref_height: float = 10.0
    target_height: float = 80.0


class FilterResponse(BaseModel):
    """Response del filtratge"""
    filtered_data: List[Dict[str, Any]]
    shear_alpha: float
    original_count: int
    filtered_count: int
    removed_count: int
    removal_percent: float


def build_dataframe(request: FilterRequest) -> pd.DataFrame:
    """Construeix DataFrame des de diferents formats d'entrada"""
    
    # Format 1: list of dicts
    if request.data is not None:
        return pd.DataFrame(request.data)
    
    # Format 2: column-based
    data = {}
    if request.timestamps is not None:
        data['timestamp'] = request.timestamps
    if request.wind_speed is not None:
        data['wind_speed'] = request.wind_speed
    if request.wind_direction is not None:
        data['wind_direction'] = request.wind_direction
    if request.temperature is not None:
        data['temperature'] = request.temperature
    
    if not data:
        raise HTTPException(
            status_code=400,
            detail="No s'han proporcionat dades. Usa 'data' o columnes individuals."
        )
    
    return pd.DataFrame(data)


@router.post("/filter", response_model=FilterResponse)
async def filter_met_endpoint(request: FilterRequest):
    """
    Aplica filtres a dades meteorològiques
    
    - remove_tower_shadow: Elimina dades afectades per ombra de torre
    - remove_ice: Elimina dades amb possible gel
    - remove_high_std: Elimina dades amb desviació estàndard alta
    - target_height: Alçada objectiu per extrapolació
    """
    try:
        # Construeix DataFrame des de qualsevol format
        df = build_dataframe(request)
        
        # Verificar columnes requerides
        required_cols = ['wind_speed', 'wind_direction']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Columnes requerides manquants: {missing}"
            )
        
        # Aplicar filtres
        result = filter_met_data(
            df,
            remove_tower_shadow=request.remove_tower_shadow,
            remove_ice=request.remove_ice,
            remove_high_std=request.remove_high_std,
            ref_height=request.ref_height,
            target_height=request.target_height
        )
        
        return FilterResponse(
            filtered_data=result['filtered_data'].to_dict(orient='records'),
            shear_alpha=result['shear_alpha'],
            original_count=result['original_count'],
            filtered_count=result['filtered_count'],
            removed_count=result['original_count'] - result['filtered_count'],
            removal_percent=(
                (result['original_count'] - result['filtered_count']) / 
                result['original_count'] * 100
                if result['original_count'] > 0 else 0
            )
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-csv")
async def upload_csv(
    file: bytes,
    remove_tower_shadow: bool = True,
    remove_ice: bool = True,
    target_height: float = 80.0
):
    """
    Puja un fitxer CSV i aplica filtres
    """
    try:
        df = pd.read_csv(io.BytesIO(file))
        
        result = filter_met_data(
            df,
            remove_tower_shadow=remove_tower_shadow,
            remove_ice=remove_ice,
            ref_height=10.0,
            target_height=target_height
        )
        
        return {
            "message": "Filtratge complet",
            "shear_alpha": result['shear_alpha'],
            "filtered_data": result['filtered_data'].to_dict(orient='records')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
