"""
Met Data Structures - Port de Met.cs (C#)

Estructures de dades per a dades meteorològiques
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class MetData:
    """
    Estructura per a dades d'una estació meteorològica
    
    Equivalent C#:
    public class Met
    """
    timestamp: datetime
    wind_speed: float      # m/s
    wind_direction: float   # graus (0-360)
    temperature: Optional[float] = None  # °C
    pressure: Optional[float] = None      # hPa
    humidity: Optional[float] = None      # %
    
    @property
    def sector(self) -> int:
        """Retorna el sector de direcció (0-11 per a 12 sectors)"""
        sector_size = 360 / 12
        return int(self.wind_direction // sector_size) % 12
    
    def to_array(self) -> np.ndarray:
        """Converteix a array numpy per càlculs"""
        return np.array([
            self.wind_speed,
            self.wind_direction,
            self.temperature or 0,
            self.pressure or 0
        ])
    
    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> 'MetData':
        """Crea MetData des d'un DataFrame row"""
        return cls(
            timestamp=row['timestamp'] if 'timestamp' in row.index else datetime.now(),
            wind_speed=row['wind_speed'],
            wind_direction=row['wind_direction'],
            temperature=row.get('temperature'),
            pressure=row.get('pressure'),
            humidity=row.get('humidity')
        )


@dataclass
class MetStats:
    """
    Estadístiques per a dades meteorològiques
    
    Equivalent C#:
    public class MetStats
    """
    mean_wind_speed: float
    std_wind_speed: float
    mean_wind_direction: float
    std_wind_direction: float
    mean_temperature: Optional[float] = None
    mean_pressure: Optional[float] = None
    count: int = 0
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'MetStats':
        """Calcula estadístiques des d'un DataFrame"""
        return cls(
            mean_wind_speed=df['wind_speed'].mean(),
            std_wind_speed=df['wind_speed'].std(),
            mean_wind_direction=_circular_mean(df['wind_direction']),
            std_wind_direction=_circular_std(df['wind_direction']),
            mean_temperature=df.get('temperature').mean() if 'temperature' in df.columns else None,
            mean_pressure=df.get('pressure').mean() if 'pressure' in df.columns else None,
            count=len(df)
        )


def _circular_mean(angles: pd.Series) -> float:
    """
    Calcula la mitjana circular per angles
    
    Equivalent C#:
    Met.Tavg(angles)
    """
    radians = np.deg2rad(angles)
    sin_mean = np.sin(radians).mean()
    cos_mean = np.cos(radians).mean()
    return np.rad2deg(np.arctan2(sin_mean, cos_mean)) % 360


def _circular_std(angles: pd.Series) -> float:
    """
    Calcula la desviació estàndard circular per angles
    
    Equivalent C#:
    Met.Tsd(angles)
    """
    radians = np.deg2rad(angles)
    sin_mean = np.sin(radians).mean()
    cos_mean = np.cos(radians).mean()
    r = np.sqrt(sin_mean**2 + cos_mean**2)
    return np.rad2deg(np.sqrt(-2 * np.log(r)))
