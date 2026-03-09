"""
Wind Map API - Open-Meteo Integration
Retorna dades de vent reals per a visualització en mapa
"""

from fastapi import APIRouter, Query
import httpx
import math

router = APIRouter(prefix="/wind-map")

# Open-Meteo API
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@router.get("/data")
async def get_wind_map_data(
    lat: float = Query(41.5, description="Latitud", ge=-90, le=90),
    lon: float = Query(2.5, description="Longitud", ge=-180, le=180), 
    hours: int = Query(24, description="Hores de predicció", ge=1, le=168)
):
    """
    Obtenir dades de vent des d'Open-Meteo per a visualització en mapa.
    
    Retorna:
    - Velocitat mitjana, màxima i mínima
    - Direcció dominant
    - Dades horàries completes
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
                    "forecast_hours": hours,
                    "timezone": "Europe/Madrid"
                },
                timeout=10.0
            )
            data = response.json()
        except Exception as e:
            return {"error": str(e), "fallback": True}
    
    hourly = data.get("hourly", {})
    wind_speeds = hourly.get("wind_speed_10m", [])
    wind_directions = hourly.get("wind_direction_10m", [])
    gusts = hourly.get("wind_gusts_10m", [])
    
    if not wind_speeds:
        return {"error": "No data available", "fallback": True}
    
    # Calcular estadístiques
    avg_speed = sum(wind_speeds) / len(wind_speeds)
    
    # Direcció dominant (vector mitjà)
    sin_sum = sum(math.sin(math.radians(d)) for d in wind_directions if d is not None)
    cos_sum = sum(math.cos(math.radians(d)) for d in wind_directions if d is not None)
    dominant_direction = (math.degrees(math.atan2(sin_sum, cos_sum)) + 360) % 360
    
    return {
        "location": {"lat": lat, "lon": lon},
        "hours": hours,
        "avg_speed": round(avg_speed, 2),
        "max_speed": round(max(wind_speeds), 2),
        "min_speed": round(min(wind_speeds), 2),
        "dominant_direction": round(dominant_direction, 0),
        "current": {
            "speed": wind_speeds[0] if wind_speeds else None,
            "direction": wind_directions[0] if wind_directions else None,
            "gusts": gusts[0] if gusts else None
        },
        "data": [
            {
                "hour": i,
                "speed": round(wind_speeds[i], 2) if i < len(wind_speeds) else None,
                "direction": round(wind_directions[i], 0) if i < len(wind_directions) else None,
                "gusts": round(gusts[i], 2) if i < len(gusts) else None
            }
            for i in range(min(hours, len(wind_speeds)))
        ]
    }


@router.get("/grid")
async def get_wind_grid(
    min_lat: float = Query(41.0, description="Latitud mínima"),
    max_lat: float = Query(42.0, description="Latitud màxima"),
    min_lon: float = Query(1.5, description="Longitud mínima"),
    max_lon: float = Query(3.0, description="Longitud màxima"),
    resolution: int = Query(5, description="Resolució de la graella", ge=3, le=15)
):
    """
    Obtenir dades de vent per a una graella d'ubicacions.
    Útil per a visualització de mapes de vent (contorns).
    """
    import numpy as np
    
    lats = np.linspace(min_lat, max_lat, resolution)
    lons = np.linspace(min_lon, max_lon, resolution)
    
    grid_data = []
    
    async with httpx.AsyncClient() as client:
        for lat in lats:
            for lon in lons:
                try:
                    response = await client.get(
                        OPEN_METEO_URL,
                        params={
                            "latitude": lat,
                            "longitude": lon,
                            "hourly": "wind_speed_10m,wind_direction_10m",
                            "forecast_hours": 1,
                            "timezone": "Europe/Madrid"
                        },
                        timeout=5.0
                    )
                    d = response.json()
                    hourly = d.get("hourly", {})
                    
                    grid_data.append({
                        "lat": round(lat, 3),
                        "lon": round(lon, 3),
                        "speed": hourly.get("wind_speed_10m", [None])[0],
                        "direction": hourly.get("wind_direction_10m", [None])[0]
                    })
                except Exception:
                    grid_data.append({
                        "lat": round(lat, 3),
                        "lon": round(lon, 3),
                        "speed": None,
                        "direction": None
                    })
    
    return {
        "grid": grid_data,
        "bounds": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon
        },
        "resolution": resolution
    }
