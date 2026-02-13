"""
WRF Data Processing Utilities for Continuum Web

Utilities per llegir, processar i exportar dades WRF:
- Lectura de fitxers NetCDF
- Càlcul de vent mig (10m equivalent)
- Generació de TIFF
- Extracció WRG (Wind Resource Grid)
- Sèries temporals
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import xarray as xr
import pandas as pd


@dataclass
class WRFData:
    """Contenidor per dades WRF processades"""
    u_component: np.ndarray  # shape: (time, lat, lon)
    v_component: np.ndarray  # shape: (time, lat, lon)
    wind_speed: np.ndarray    # shape: (time, lat, lon)
    wind_direction: np.ndarray # shape: (time, lat, lon)
    latitude: np.ndarray      # shape: (lat, lon)
    longitude: np.ndarray     # shape: (lat, lon)
    time: np.ndarray          # shape: (time,)
    attributes: dict


class WRFReader:
    """
    Lector de fitxers WRF NetCDF
    
    Args:
        filepath: Path al fitxer NetCDF
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.dataset: Optional[xr.Dataset] = None
        self.attributes = {}
    
    def read(self) -> WRFData:
        """Llegeix el fitxer WRF i retorna dades processades"""
        self.dataset = xr.open_dataset(self.filepath)
        
        # Extreure components del vent
        # El nivell 0 (28) és el més proper a la superfície
        u = self.dataset['U'].sel(lev=28).values
        v = self.dataset['V'].sel(lev=28).values
        
        # Corregir per lat/lon (U és a les cares E-W, V a les cares N-S)
        # Per dades WRF típiques, U i V ja vénen interpolades
        # Fem servir la mitjana per igualar dimensions
        if u.shape[1] > self.dataset['lat'].shape[0]:
            u = u[:, :self.dataset['lat'].shape[0], :self.dataset['lon'].shape[1]]
        if v.shape[1] > self.dataset['lat'].shape[0]:
            v = v[:, :self.dataset['lat'].shape[0], :self.dataset['lon'].shape[1]]
        
        # Calcular velocitat i direcció
        wind_speed = np.sqrt(u**2 + v**2)
        wind_direction = (np.degrees(np.arctan2(-u, -v)) + 360) % 360
        
        # Extreure coords i temps
        lat = self.dataset['lat'].values
        lon = self.dataset['lon'].values
        time = self.dataset['time'].values
        
        # Crear meshgrid si lat/lon són 1D
        if lat.ndim == 1 and lon.ndim == 1:
            lon_2d, lat_2d = np.meshgrid(lon, lat)
        else:
            lat_2d = lat
            lon_2d = lon
        
        # Atributs
        self.attributes = {
            'source_file': self.filepath,
            'time_range': f"{time[0]} to {time[-1]}",
            'n_times': len(time),
            'grid_shape': lat_2d.shape,
            'resolution': 'd05 (alta)' if 'd05' in self.filepath else ('d02 (baixa)' if 'd02' in self.filepath else 'd04 (mitja)')
        }
        
        return WRFData(
            u_component=u,
            v_component=v,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            latitude=lat_2d,
            longitude=lon_2d,
            time=time,
            attributes=self.attributes
        )
    
    def calculate_daily_mean(self, wrf_data: WRFData) -> dict:
        """
        Calcula el vent mig diari
        
        Returns:
            Dict amb estadístiques diàries
        """
        mean_ws = np.nanmean(wrf_data.wind_speed)
        max_ws = np.nanmax(wrf_data.wind_speed)
        min_ws = np.nanmin(wrf_data.wind_speed)
        std_ws = np.nanstd(wrf_data.wind_speed)
        
        # Direcció predominant (mitjana vectorial)
        u_mean = np.nanmean(wrf_data.u_component)
        v_mean = np.nanmean(wrf_data.v_component)
        mean_dir = (np.degrees(np.arctan2(-u_mean, -v_mean)) + 360) % 360
        
        # Percentils
        p10 = np.nanpercentile(wrf_data.wind_speed, 10)
        p50 = np.nanpercentile(wrf_data.wind_speed, 50)
        p90 = np.nanpercentile(wrf_data.wind_speed, 90)
        
        return {
            'mean_wind_speed_ms': mean_ws,
            'max_wind_speed_ms': max_ws,
            'min_wind_speed_ms': min_ws,
            'std_wind_speed_ms': std_ws,
            'mean_wind_direction_deg': mean_dir,
            'percentile_10': p10,
            'percentile_50': p50,
            'percentile_90': p90,
            'n_hours': len(wrf_data.time),
            'date': str(wrf_data.time[0])[:10]
        }
    
    def extract_time_series(
        self, 
        wrf_data: WRFData,
        lat_idx: Optional[int] = None,
        lon_idx: Optional[int] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Extreu sèrie temporal en un punt
        
        Args:
            lat_idx/lon_idx: Índexs del punt
            lat/lon: Coordenades del punt (busca el més proper)
        """
        if lat is not None and lon is not None:
            # Trobar índex més proper
            lat_idx = np.abs(wrf_data.latitude[:, 0] - lat).argmin()
            lon_idx = np.abs(wrf_data.longitude[0, :] - lon).argmin()
        
        if lat_idx is None:
            lat_idx = wrf_data.latitude.shape[0] // 2
        if lon_idx is None:
            lon_idx = wrf_data.longitude.shape[1] // 2
        
        # Extreure valors
        ws = wrf_data.wind_speed[:, lat_idx, lon_idx]
        wd = wrf_data.wind_direction[:, lat_idx, lon_idx]
        u = wrf_data.u_component[:, lat_idx, lon_idx]
        v = wrf_data.v_component[:, lat_idx, lon_idx]
        
        # Crear DataFrame
        df = pd.DataFrame({
            'datetime': pd.to_datetime(wrf_data.time),
            'wind_speed_ms': ws,
            'wind_direction_deg': wd,
            'u_component': u,
            'v_component': v
        })
        
        df = df.set_index('datetime')
        
        return df
    
    def calculate_hourly_statistics(self, wrf_data: WRFData) -> pd.DataFrame:
        """
        Calcula estadístiques per cada hora del dia
        """
        df = self.extract_time_series(wrf_data)
        df['hour'] = df.index.hour
        
        hourly = df.groupby('hour').agg({
            'wind_speed_ms': ['mean', 'std', 'min', 'max'],
            'wind_direction_deg': 'mean'
        })
        
        hourly.columns = ['_'.join(col) for col in hourly.columns]
        hourly = hourly.reset_index()
        
        return hourly


def read_wrf_file(filepath: str) -> WRFData:
    """Funció d'utilitat per llegir WRF"""
    reader = WRFReader(filepath)
    return reader.read()


def calculate_windrose(wrf_data: WRFData, n_sectors: int = 12) -> dict:
    """
    Calcula la rosa dels vents des de dades WRF
    
    Args:
        wrf_data: Dades WRF processades
        n_sectors: Nombre de sectors (default 12 = 30° cada)
    
    Returns:
        Dict amb frequència per sector
    """
    sectors = 360 // n_sectors
    sector_counts = np.zeros(n_sectors)
    mean_speeds = np.zeros(n_sectors)
    
    for i in range(n_sectors):
        mask = (wrf_data.wind_direction >= i * sectors) & \
               (wrf_data.wind_direction < (i + 1) * sectors)
        
        if mask.sum() > 0:
            sector_counts[i] = mask.sum()
            mean_speeds[i] = np.mean(wrf_data.wind_speed[mask])
    
    total = sector_counts.sum()
    frequencies = sector_counts / total * 100 if total > 0 else np.zeros(n_sectors)
    
    return {
        'sectors': [f"{i * sectors}-{(i + 1) * sectors}°" for i in range(n_sectors)],
        'frequencies_percent': frequencies.tolist(),
        'mean_speeds_ms': mean_speeds.tolist(),
        'n_sectors': n_sectors
    }
