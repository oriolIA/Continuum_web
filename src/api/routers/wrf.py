"""
WRF API Router

Endpoints per processar dades WRF:
- Lectura de fitxers NetCDF
- Generació de WRG, TIFF, CSV
- Sèries temporals
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import os

from src.calculations.wrf import (
    WRFReader,
    WRGGenerator,
    GeoTIFFGenerator,
    TimeSeriesExporter,
    calculate_windrose
)


router = APIRouter(prefix="/wrf", tags=["WRF Data Processing"])


class WRFLoadRequest(BaseModel):
    """Request per carregar fitxer WRF"""
    filepath: str


class WRFStatsResponse(BaseModel):
    """Response amb estadístiques"""
    date: str
    mean_wind_speed_ms: float
    max_wind_speed_ms: float
    min_wind_speed_ms: float
    std_wind_speed_ms: float
    mean_wind_direction_deg: float
    percentile_10: float
    percentile_50: float
    percentile_90: float
    n_hours: int


class WRGSummaryResponse(BaseModel):
    """Response del resum WRG"""
    mean_wind_speed_ms: float
    max_wind_speed_ms: float
    p50_ms: float
    p75_ms: float
    p90_ms: float
    capacity_factor_estimate: float
    area_km2: float
    dominant_direction_deg: float


class WindRoseResponse(BaseModel):
    """Response de la rosa del vents"""
    sectors: list[str]
    frequencies_percent: list[float]
    mean_speeds_ms: list[float]
    n_sectors: int


class TimeSeriesPointRequest(BaseModel):
    """Request per punt de sèrie temporal"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lat_idx: Optional[int] = None
    lon_idx: Optional[int] = None


@router.post("/load")
async def load_wrf_file(request: WRFLoadRequest):
    """
    Carrega un fitxer WRF NetCDF
    
    Args:
        filepath: Path al fitxer NetCDF
    
    Returns:
        Resum de les dades carregades
    """
    if not os.path.exists(request.filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {request.filepath}")
    
    try:
        reader = WRFReader(request.filepath)
        wrf_data = reader.read()
        
        return {
            "status": "loaded",
            "filepath": request.filepath,
            "attributes": wrf_data.attributes,
            "shape": {
                "time": len(wrf_data.time),
                "latitude": wrf_data.latitude.shape,
                "longitude": wrf_data.longitude.shape
            },
            "time_range": {
                "start": str(wrf_data.time[0]),
                "end": str(wrf_data.time[-1])
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats", response_model=WRFStatsResponse)
async def get_wrf_stats(request: WRFLoadRequest):
    """
    Calcula estadístiques del fitxer WRF
    """
    if not os.path.exists(request.filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {request.filepath}")
    
    try:
        reader = WRFReader(request.filepath)
        wrf_data = reader.read()
        stats = reader.calculate_daily_mean(wrf_data)
        
        return WRFStatsResponse(**stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wrg", response_model=WRGSummaryResponse)
async def generate_wrg(request: WRFLoadRequest):
    """
    Genera resum WRG (Wind Resource Grid)
    """
    if not os.path.exists(request.filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {request.filepath}")
    
    try:
        reader = WRFReader(request.filepath)
        wrf_data = reader.read()
        
        generator = WRGGenerator(wrf_data)
        summary = generator.get_wind_resource_summary()
        
        return WRGSummaryResponse(**summary)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wrg/download")
async def download_wrg(
    filepath: str = Query(..., description="Path al fitxer WRF"),
    include_direction: bool = Query(True, description="Incloure direcció")
):
    """
    Descarrega contingut WRG com a text
    """
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {filepath}")
    
    try:
        reader = WRFReader(filepath)
        wrf_data = reader.read()
        
        generator = WRGGenerator(wrf_data)
        content = generator.generate_wrg_content(include_direction)
        
        return {"content": content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ascii/download")
async def download_ascii_grid(
    filepath: str = Query(..., description="Path al fitxer WRF"),
    variable: str = Query('wind_speed', description="Variable: wind_speed, u, v, direction"),
    statistic: str = Query('mean', description="Estadística: mean, max, min, std")
):
    """
    Descarrega ASCII Grid del camp de vent
    """
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {filepath}")
    
    try:
        reader = WRFReader(filepath)
        wrf_data = reader.read()
        
        generator = GeoTIFFGenerator(wrf_data)
        content = generator.export_ascii_grid(variable, statistic)
        
        return {
            "content": content,
            "metadata": generator.generate_metadata(variable, statistic)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/timeseries")
async def get_timeseries(
    filepath: str = Query(..., description="Path al fitxer WRF"),
    request: TimeSeriesPointRequest = None
):
    """
    Extreu sèrie temporal en un punt
    """
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {filepath}")
    
    try:
        reader = WRFReader(filepath)
        wrf_data = reader.read()
        
        ts = reader.extract_time_series(
            wrf_data,
            lat_idx=request.lat_idx if request else None,
            lon_idx=request.lon_idx if request else None,
            lat=request.latitude if request else None,
            lon=request.longitude if request else None
        )
        
        return {
            "timeseries": ts.to_dict(orient='records'),
            "point": {
                "lat_idx": request.lat_idx if request else None,
                "lon_idx": request.lon_idx if request else None,
                "latitude": request.latitude if request else None,
                "longitude": request.longitude if request else None
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/windrose", response_model=WindRoseResponse)
async def get_windrose(
    filepath: str = Query(..., description="Path al fitxer WRF"),
    n_sectors: int = Query(12, description="Nombre de sectors")
):
    """
    Calcula rosa del vents
    """
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {filepath}")
    
    try:
        reader = WRFReader(filepath)
        wrf_data = reader.read()
        
        rose = calculate_windrose(wrf_data, n_sectors)
        
        return WindRoseResponse(**rose)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-day")
async def process_wrf_day(
    filepath: str = Query(..., description="Path al fitxer WRF NetCDF"),
    output_dir: str = Query('.', description="Directori de sortida"),
    prefix: str = Query('', description="Prefix pels fitxers")
):
    """
    Processa un dia WRF complet i genera tots els outputs
    """
    from src.calculations.wrf import process_wrf_day
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Fitxer no trobat: {filepath}")
    
    try:
        result = process_wrf_day(filepath, output_dir, prefix)
        
        return {
            "status": "processed",
            "date": result['date'],
            "outputs": result['outputs'],
            "daily_mean": result['daily_mean']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
