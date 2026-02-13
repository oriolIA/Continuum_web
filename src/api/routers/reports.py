"""
Reports API Router

Endpoints per generar reports de vent:
- Histograma
- Rosa del vents
- Distribució Weibull
- Vents extrems
- Turbulència
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import numpy as np
import pandas as pd

from src.calculations.reports.wind_report import WindReport, WindReportConfig, generate_report_from_dataframe


router = APIRouter(prefix="/reports", tags=["Wind Reports"])


class ReportRequest(BaseModel):
    """Request per generar report"""
    wind_speeds: List[float]
    wind_directions: List[float]
    datetimes: Optional[List[str]] = None
    n_sectors: int = 12
    n_hist_bins: int = 20
    extreme_threshold: float = 15.0


class HistogramResponse(BaseModel):
    """Response de l'histograma"""
    bin_edges: List[float]
    bin_centers: List[float]
    counts: List[int]
    total_samples: int
    mean_speed: float
    std_speed: float


class WindRoseResponse(BaseModel):
    """Response de la rosa del vents"""
    sectors: List[str]
    frequencies_percent: List[float]
    mean_speeds_ms: List[float]
    max_speeds_ms: List[float]
    n_sectors: int
    dominant_sector: str
    prevailing_direction: str


class WeibullResponse(BaseModel):
    """Response del ajust Weibull"""
    k_shape: float
    A_scale_ms: float
    mean_weibull_ms: float
    mean_empirical_ms: float
    aep_factor: float


class ExtremesResponse(BaseModel):
    """Response dels vents extrems"""
    threshold_ms: float
    n_extreme_events: int
    extreme_percent: float
    percentile_99_ms: float
    max_speed_ms: float
    extreme_directions: dict


class FullReportResponse(BaseModel):
    """Report complet"""
    summary: dict
    histogram: dict
    wind_rose: dict
    weibull: dict
    extreme_winds: dict
    hourly: dict
    monthly: dict
    turbulence: dict


@router.post("/histogram", response_model=HistogramResponse)
async def get_histogram(request: ReportRequest):
    """
    Genera histograma de velocitats
    """
    try:
        report = WindReport(
            np.array(request.wind_speeds),
            np.array(request.wind_directions)
        )
        hist = report.histogram(request.n_hist_bins)
        
        return HistogramResponse(
            **hist,
            mean_speed=float(np.mean(request.wind_speeds)),
            std_speed=float(np.std(request.wind_speeds))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wind-rose", response_model=WindRoseResponse)
async def get_wind_rose(request: ReportRequest):
    """
    Genera rosa del vents
    """
    try:
        report = WindReport(
            np.array(request.wind_speeds),
            np.array(request.wind_directions)
        )
        rose = report.wind_rose(request.n_sectors)
        
        return WindRoseResponse(**rose)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weibull", response_model=WeibullResponse)
async def get_weibull(request: ReportRequest):
    """
    Ajust de distribució Weibull
    """
    try:
        report = WindReport(
            np.array(request.wind_speeds),
            np.array(request.wind_directions)
        )
        wb = report.weibull_fit()
        
        if 'error' in wb:
            raise HTTPException(status_code=400, detail=wb['error'])
        
        return WeibullResponse(**wb)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extremes", response_model=ExtremesResponse)
async def get_extremes(request: ReportRequest):
    """
    Anàlisi de vents extrems
    """
    try:
        report = WindReport(
            np.array(request.wind_speeds),
            np.array(request.wind_directions)
        )
        ext = report.extreme_winds(request.extreme_threshold)
        
        return ExtremesResponse(**ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full", response_model=FullReportResponse)
async def get_full_report(request: ReportRequest):
    """
    Report complet amb totes les mètriques
    """
    try:
        report = WindReport(
            np.array(request.wind_speeds),
            np.array(request.wind_directions)
        )
        
        config = WindReportConfig(
            n_sectors=request.n_sectors,
            n_hist_bins=request.n_hist_bins,
            extreme_threshold=request.extreme_threshold
        )
        
        full = report.full_report(config)
        
        return FullReportResponse(**full)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-csv")
async def report_from_csv(
    filepath: str = Query(..., description="Path al fitxer CSV"),
    speed_col: str = Query('wind_speed', description="Columna de velocitat"),
    direction_col: str = Query('wind_direction', description="Columna de direcció"),
    time_col: str = Query(None, description="Columna de temps")
):
    """
    Genera report des de fitxer CSV
    """
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_csv(filepath, delim_whitespace=True)
        
        report = generate_report_from_dataframe(
            df, speed_col, direction_col, time_col
        )
        
        return report
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/turbulence")
async def get_turbulence(
    wind_speeds: List[float],
    std_window: int = Query(10, description="Mida de finestra per STD")
):
    """
    Calcula intensitat de turbulència
    """
    try:
        speeds = np.array(wind_speeds)
        
        # Calcular STD mòbil
        rolling_std = pd.Series(speeds).rolling(std_window, center=True).std()
        rolling_mean = pd.Series(speeds).rolling(std_window, center=True).mean()
        
        valid = ~rolling_std.isna() & ~rolling_mean.isna() & (rolling_mean > 0)
        ti = rolling_std[valid] / rolling_mean[valid]
        
        return {
            "ti_mean": float(ti.mean()),
            "ti_std": float(ti.std()),
            "ti_max": float(ti.max()),
            "ti_percentile_90": float(np.percentile(ti, 90)),
            "n_samples_valid": int(valid.sum())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly")
async def get_hourly_distribution(
    wind_speeds: List[float],
    wind_directions: List[float],
    datetimes: List[str]
):
    """
    Distribució horària del vent
    """
    try:
        time_index = pd.to_datetime(datetimes)
        
        report = WindReport(
            np.array(wind_speeds),
            np.array(wind_directions),
            time_index
        )
        
        return report.hourly_distribution()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
