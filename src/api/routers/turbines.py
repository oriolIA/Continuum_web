"""
Turbines API Router

Endpoints per gestionar turbines i càlculs d'energia:
- Catàleg de turbines
- Corbes de potència
- AEP calculations
- Comparació de models
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import numpy as np

from src.calculations.turbines import (
    TURBINE_CATALOG,
    get_turbine,
    list_turbines,
    compare_turbines,
    estimate_park_energy
)


router = APIRouter(prefix="/turbines", tags=["Turbines"])


class TurbineListItem(BaseModel):
    """Item de la llista de turbines"""
    id: str
    name: str
    manufacturer: str
    rated_power_mw: float
    rotor_diameter_m: float
    hub_height_m: float
    iec_class: str


class TurbineDetail(BaseModel):
    """Detall d'una turbina"""
    name: str
    manufacturer: str
    rated_power_kw: float
    rotor_diameter_m: float
    hub_height_m: float
    cut_in_speed_ms: float
    cut_out_speed_ms: float
    rated_wind_speed_ms: float
    thrust_coefficient: float
    IEC_class: str
    power_curve: dict


class PowerCurveRequest(BaseModel):
    """Request per corba de potència"""
    wind_speeds: List[float]


class PowerCurveResponse(BaseModel):
    """Response de la corba de potència"""
    turbine: str
    wind_speeds: List[float]
    powers_kw: List[float]


class AEPRequest(BaseModel):
    """Request per càlcul AEP"""
    turbine_model: str
    mean_wind_speed_ms: float
    wind_rose: dict = None  # Opcional: sectors com a percentatge


class AEPResponse(BaseModel):
    """Response del càlcul AEP"""
    turbine: str
    gross_aep_mwh: float
    net_aep_mwh: float
    capacity_factor_gross: float
    capacity_factor_net: float
    equivalent_hours: float
    losses_breakdown: dict


class CompareRequest(BaseModel):
    """Request per comparar turbines"""
    turbine_names: List[str]
    wind_speed_ms: float


class CompareResponse(BaseModel):
    """Response de la comparació"""
    wind_speed_ms: float
    comparison: List[dict]


class ParkEnergyRequest(BaseModel):
    """Request per energia del parc"""
    turbine_model: str
    n_turbines: int
    mean_wind_speed_ms: float
    wind_rose: dict
    spacing_x_diameters: float = 5
    spacing_y_diameters: float = 7


@router.get("/list", response_model=List[TurbineListItem])
async def list_available_turbines():
    """
    Llista totes les turbines disponibles
    """
    turbines = list_turbines()
    return turbines


@router.get("/{turbine_id}", response_model=TurbineDetail)
async def get_turbine_detail(turbine_id: str):
    """
    Retorna detall d'una turbina específica
    """
    turbine = get_turbine(turbine_id)
    
    if turbine is None:
        raise HTTPException(status_code=404, detail=f"Turbine '{turbine_id}' not found")
    
    pc = turbine.power_curve
    
    return TurbineDetail(
        name=turbine.name,
        manufacturer=turbine.manufacturer,
        rated_power_kw=turbine.rated_power_kw,
        rotor_diameter_m=turbine.rotor_diameter_m,
        hub_height_m=turbine.hub_height_m,
        cut_in_speed_ms=turbine.cut_in_speed_ms,
        cut_out_speed_ms=turbine.cut_out_speed_ms,
        rated_wind_speed_ms=turbine.rated_wind_speed_ms,
        thrust_coefficient=turbine.thrust_coefficient,
        IEC_class=turbine.IEC_class,
        power_curve={
            "wind_speeds": pc.wind_speeds,
            "powers": pc.powers,
            "cut_in": pc.cut_in,
            "cut_out": pc.cut_out,
            "rated": pc.rated,
            "rated_wind_speed": pc.rated_wind_speed
        }
    )


@router.post("/power-curve", response_model=PowerCurveResponse)
async def get_power_curve(request: PowerCurveRequest):
    """
    Retorna la corba de potència per a velocitats donades
    """
    # Buscar a primera turbina disponible
    turbine_id = list(TURBINE_CATALOG.keys())[0]
    turbine = get_turbine(turbine_id)
    
    if turbine is None:
        raise HTTPException(status_code=500, detail="No turbines available")
    
    powers = [turbine.power_curve.get_power(ws) for ws in request.wind_speeds]
    
    return PowerCurveResponse(
        turbine=turbine.name,
        wind_speeds=request.wind_speeds,
        powers_kw=[round(p, 1) for p in powers]
    )


@router.post("/power-curve/{turbine_id}", response_model=PowerCurveResponse)
async def get_turbine_power_curve(turbine_id: str, request: PowerCurveRequest):
    """
    Retorna la corba de potència d'una turbina específica
    """
    turbine = get_turbine(turbine_id)
    
    if turbine is None:
        raise HTTPException(status_code=404, detail=f"Turbine '{turbine_id}' not found")
    
    powers = [turbine.power_curve.get_power(ws) for ws in request.wind_speeds]
    
    return PowerCurveResponse(
        turbine=turbine.name,
        wind_speeds=request.wind_speeds,
        powers_kw=[round(p, 1) for p in powers]
    )


@router.post("/aep", response_model=AEPResponse)
async def calculate_aep(request: AEPRequest):
    """
    Calcula l'Annual Energy Production per una turbina
    """
    turbine = get_turbine(request.turbine_model)
    
    if turbine is None:
        raise HTTPException(status_code=404, detail=f"Turbine '{request.turbine_model}' not found")
    
    # Usar wind_rose o estimar
    wind_rose = request.wind_rose or {f"{i*30}-{(i+1)*30}°": 100/12 for i in range(12)}
    
    aep = turbine.annual_energy_production(
        request.mean_wind_speed_ms,
        wind_rose
    )
    
    return AEPResponse(
        turbine=turbine.name,
        **aep
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_turbine_models(request: CompareRequest):
    """
    Compara múltiples turbines a una velocitat donada
    """
    turbines_data = []
    
    for name in request.turbine_names:
        turbine = get_turbine(name)
        if turbine:
            power = turbine.power_curve.get_power(request.wind_speed_ms)
            cf = power / turbine.rated_power_kw * 100 if turbine.rated_power_kw > 0 else 0
            
            turbines_data.append({
                "turbine": turbine.name,
                "manufacturer": turbine.manufacturer,
                "rated_power_mw": turbine.rated_power_kw / 1000,
                "power_at_ws_kw": round(power, 1),
                "capacity_factor_percent": round(cf, 1),
                "rotor_diameter_m": turbine.rotor_diameter_m
            })
    
    return CompareResponse(
        wind_speed_ms=request.wind_speed_ms,
        comparison=turbines_data
    )


@router.post("/park-energy")
async def calculate_park_energy(request: ParkEnergyRequest):
    """
    Calcula energia per un parc eòlic
    """
    turbine = get_turbine(request.turbine_model)
    
    if turbine is None:
        raise HTTPException(status_code=404, detail=f"Turbine '{request.turbine_model}' not found")
    
    turbines = [turbine] * request.n_turbines
    
    energy = estimate_park_energy(
        turbines,
        request.mean_wind_speed_ms,
        request.wind_rose,
        request.spacing_x_diameters,
        request.spacing_y_diameters
    )
    
    return energy


@router.get("/iec-classes")
async def get_iec_classes():
    """
    Retorna les classes IEC disponibles
    """
    return {
        "classes": ["I", "II", "III", "S"],
        "descriptions": {
            "I": "High wind (Vavg > 10 m/s)",
            "II": "Medium wind (8.5 < Vavg <= 10 m/s)",
            "III": "Low wind (Vavg <= 8.5 m/s)",
            "S": "Special (custom requirements)"
        }
    }
