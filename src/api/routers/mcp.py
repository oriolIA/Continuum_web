"""
MCP API Router

Endpoints per a Measure-Correlate-Predict
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from src.calculations.mcp import MCP, MCPConfig


router = APIRouter(prefix="/mcp", tags=["MCP - Measure-Correlate-Predict"])


class MCPRequest(BaseModel):
    """Request per MCP"""
    reference_data: list[dict]
    target_data: list[dict]
    method: str = "orthogonal"  # orthogonal, bins, matrix
    sectors: int = 12
    reference_name: str = "reference"
    target_name: str = "target"


class SectorResult(BaseModel):
    sector: int
    direction_range: tuple[float, float]
    slope: float
    intercept: float
    correlation: float
    uncertainty: float
    n_samples: int


class MCPResponse(BaseModel):
    method: str
    global_slope: float
    global_intercept: float
    global_correlation: float
    sectors: list[SectorResult]
    uncertainty_summary: dict
    predicted_data: list[dict]


@router.post("/analyze", response_model=MCPResponse)
async def run_mcp(request: MCPRequest):
    """
    Executa MCP entre dues estacions
    
    Args:
        reference_data: Dades de l'estació de referència
        target_data: Dades de l'estació objectiu
        method: Mètode (orthogonal, bins, matrix)
        sectors: Nombre de sectors per anàlisi sectorial
    """
    try:
        # Convertir a DataFrames
        ref_df = pd.DataFrame(request.reference_data)
        target_df = pd.DataFrame(request.target_data)
        
        # Verificar columnes requerides
        for df, name in [(ref_df, "reference"), (target_df, "target")]:
            if 'wind_speed' not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"{name}: Columna 'wind_speed' requerida"
                )
        
        # Configurar i executar MCP
        config = MCPConfig(
            reference_station=request.reference_name,
            target_station=request.target_name,
            method=request.method,
            sectors=request.sectors
        )
        
        mcp = MCP(config)
        result = mcp.run(ref_df, target_df)
        
        # Construir resposta
        return MCPResponse(
            method=result.method,
            global_slope=result.global_slope,
            global_intercept=result.global_intercept,
            global_correlation=result.global_correlation,
            sectors=[
                SectorResult(
                    sector=s.sector,
                    direction_range=s.direction_range,
                    slope=s.slope,
                    intercept=s.intercept,
                    correlation=s.correlation,
                    uncertainty=s.uncertainty,
                    n_samples=s.n_samples
                )
                for s in result.sector_results
            ],
            uncertainty_summary=result.uncertainty_summary,
            predicted_data=result.predicted_data.to_dict(orient='records')
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict")
async def predict_with_mcp(
    reference_values: list[float],
    method: str = "orthogonal",
    slope: float = 1.0,
    intercept: float = 0.0
):
    """
    Prediu velocitats usant paràmetres de MCP pre-calculats
    
    Args:
        reference_values: Valors de l'estació de referència
        slope: Pendent de la regressió
        intercept: Intercept de la regressió
    """
    predicted = [slope * v + intercept for v in reference_values]
    
    return {
        "input": reference_values,
        "predicted": predicted,
        "slope": slope,
        "intercept": intercept
    }
