"""
WRF Output Generators - TIFF, WRG, CSV Exports

Funcions per exportar dades WRF a diferents formats:
- GeoTIFF: Imatges georeferenciades del camp de vent
- WRG: Wind Resource Grid format
- CSV: Dades tabulades
"""

from typing import Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass

from .wrf_reader import WRFData, WRFReader


@dataclass
class GeoTIFFConfig:
    """Configuració per export GeoTIFF"""
    variable: str = 'wind_speed'  # wind_speed, u, v, direction
    statistic: str = 'mean'       # mean, max, min, std
    epsg: int = 4326              # WGS84


class GeoTIFFGenerator:
    """
    Generador de GeoTIFF des de dades WRF
    
    Args:
        wrf_data: Dades WRF processades
    """
    
    def __init__(self, wrf_data: WRFData):
        self.wrf_data = wrf_data
        self.lat = wrf_data.latitude
        self.lon = wrf_data.longitude
    
    def _get_data_array(self, variable: str, statistic: str) -> np.ndarray:
        """Extreu l'array de dades segons variable i estadística"""
        if variable == 'wind_speed':
            data = self.wrf_data.wind_speed
        elif variable == 'u':
            data = self.wrf_data.u_component
        elif variable == 'v':
            data = self.wrf_data.v_component
        elif variable == 'direction':
            data = self.wrf_data.wind_direction
        else:
            raise ValueError(f"Variable desconeguda: {variable}")
        
        if statistic == 'mean':
            return np.nanmean(data, axis=0)
        elif statistic == 'max':
            return np.nanmax(data, axis=0)
        elif statistic == 'min':
            return np.nanmin(data, axis=0)
        elif statistic == 'std':
            return np.nanstd(data, axis=0)
        else:
            raise ValueError(f"Estadística desconeguda: {statistic}")
    
    def _get_geotransform(self) -> Tuple[float, float, float, float, float, float]:
        """
        Calcula el GeoTransform per GeoTIFF
        
        Returns:
            (min_lon, pixel_width, 0, max_lat, 0, -pixel_height)
        """
        min_lon = np.nanmin(self.lon)
        max_lon = np.nanmax(self.lon)
        min_lat = np.nanmin(self.lat)
        max_lat = np.nanmax(self.lat)
        
        n_cols = self.lon.shape[1]
        n_rows = self.lat.shape[0]
        
        pixel_width = (max_lon - min_lon) / (n_cols - 1)
        pixel_height = (max_lat - min_lat) / (n_rows - 1)
        
        return (min_lon, pixel_width, 0, max_lat, 0, -pixel_height)
    
    def generate_metadata(self, variable: str, statistic: str) -> dict:
        """
        Genera metadades per al GeoTIFF
        
        Returns:
            Dict amb metadades GDAL
        """
        data = self._get_data_array(variable, statistic)
        gt = self._get_geotransform()
        
        return {
            'variable': variable,
            'statistic': statistic,
            'shape': data.shape,
            'geotransform': gt,
            'projection': 'EPSG:4326',
            'date': str(self.wrf_data.time[0])[:10],
            'n_hours': len(self.wrf_data.time),
            'units': 'm/s' if variable in ['wind_speed', 'u', 'v'] else 'degrees',
            'nodata': np.nan,
            'min_value': float(np.nanmin(data)),
            'max_value': float(np.nanmax(data)),
            'mean_value': float(np.nanmean(data))
        }
    
    def export_ascii_grid(self, variable: str = 'wind_speed', statistic: str = 'mean') -> str:
        """
        Exporta com Arc/ASCII Grid (format text simple)
        
        Returns:
            Contingut del fitxer ASCII Grid
        """
        data = self._get_data_array(variable, statistic)
        gt = self._get_geotransform()
        
        ncols = data.shape[1]
        nrows = data.shape[0]
        xllcorner = gt[0]
        yllcorner = gt[3] - nrows * abs(gt[5])
        cellsize = gt[1]
        nodata_value = -9999
        
        # Crear header
        header = f"""ncols {ncols}
nrows {nrows}
xllcorner {xllcorner:.6f}
yllcorner {yllcorner:.6f}
cellsize {cellsize:.6f}
nodata_value {nodata_value}
"""
        
        # Reformatejar dades
        data[data == np.nan] = nodata_value
        
        rows = []
        for i in range(nrows):
            row = ' '.join([f'{v:.4f}' for v in data[i, :]])
            rows.append(row)
        
        return header + '\n'.join(rows)
    
    def export_csv_summary(self) -> str:
        """
        Exporta resum estadístic a CSV
        
        Returns:
            Contingut CSV
        """
        reader = WRFReader('')
        daily = reader.calculate_daily_mean(self.wrf_data)
        
        # Convertir a CSV
        lines = ['key,value']
        for k, v in daily.items():
            lines.append(f'{k},{v}')
        
        return '\n'.join(lines)


class WRGGenerator:
    """
    Generador de Wind Resource Grid (WRG)
    
    Format WRG típic:
    - Header amb metadades
    - Matriu de velocitats
    - Matriu de direccions (opcional)
    """
    
    def __init__(self, wrf_data: WRFData):
        self.wrf_data = wrf_data
    
    def generate_wrg_content(
        self,
        include_direction: bool = True
    ) -> str:
        """
        Genera contingut WRG
        
        Args:
            include_direction: Incloure direcció del vent
        
        Returns:
            Contingut WRG formatat
        """
        ws_mean = np.nanmean(self.wrf_data.wind_speed, axis=0)
        wd_mean = np.nanmean(self.wrf_data.wind_direction, axis=0)
        
        lat = self.wrf_data.latitude
        lon = self.wrf_data.longitude
        
        # Header
        header = f"""WRG VERSION 1.0
SOURCE: WRF Model Output
DATE: {str(self.wrf_data.time[0])[:10]}
DOMAIN: {self.wrf_data.attributes.get('resolution', 'unknown')}
NROWS {lat.shape[0]}
NCOLS {lat.shape[1]}
XLLCORNER {np.nanmin(lon):.6f}
YLLCORNER {np.nanmin(lat):.6f}
CELLSIZE {abs(lon[0,1] - lon[0,0]):.6f}
NODATA -9999.0
VARIABLE WIND_SPEED
UNIT m/s
"""
        
        # Dades de velocitat
        ws_lines = []
        for row in ws_mean:
            ws_lines.append(' '.join([f'{v:.2f}' for v in row]))
        
        ws_data = '\n'.join(ws_lines)
        
        if include_direction:
            header += 'VARIABLE WIND_DIRECTION\nUNIT degrees\n'
            wd_lines = []
            for row in wd_mean:
                wd_lines.append(' '.join([f'{v:.1f}' for v in row]))
            wd_data = '\n'.join(wd_lines)
        else:
            wd_data = ''
        
        return header + ws_data + '\n' + wd_data
    
    def export_wrg_file(self, filepath: str, include_direction: bool = True):
        """
        Desa el WRG a un fitxer
        
        Args:
            filepath: Path de sortida
            include_direction: Incloure direcció
        """
        content = self.generate_wrg_content(include_direction)
        with open(filepath, 'w') as f:
            f.write(content)
    
    def get_wind_resource_summary(self) -> dict:
        """
        Retorna resum del recurs eòlic
        
        Returns:
            Dict amb estadístiques del recurs
        """
        ws = self.wrf_data.wind_speed
        
        return {
            'mean_wind_speed_ms': float(np.nanmean(ws)),
            'max_wind_speed_ms': float(np.nanmax(ws)),
            'p50_ms': float(np.nanpercentile(ws, 50)),
            'p75_ms': float(np.nanpercentile(ws, 75)),
            'p90_ms': float(np.nanpercentile(ws, 90)),
            'capacity_factor_estimate': float(np.nanmean(ws) / 12.0),  # Assumint 12 m/s nominal
            'area_km2': float(ws.shape[0] * ws.shape[1] * 3),  # ~3 km² per cel·la
            'dominant_direction_deg': float(np.nanmean(self.wrf_data.wind_direction))
        }


class TimeSeriesExporter:
    """
    Exportador de sèries temporals WRF
    """
    
    def __init__(self, wrf_data: WRFData):
        self.wrf_data = wrf_data
    
    def export_full_timeseries(self, filepath: str):
        """
        Exporta sèrie temporal completa a CSV
        
        Args:
            filepath: Path de sortida
        """
        reader = WRFReader('')
        ts = reader.extract_time_series(self.wrf_data)
        ts.to_csv(filepath)
    
    def export_hourly_summary(self, filepath: str):
        """
        Exporta resum horari a CSV
        
        Args:
            filepath: Path de sortida
        """
        reader = WRFReader('')
        hourly = reader.calculate_hourly_statistics(self.wrf_data)
        hourly.to_csv(filepath, index=False)
    
    def export_daily_summary(self, filepath: str):
        """
        Exporta resum diari a CSV
        
        Args:
            filepath: Path de sortida
        """
        reader = WRFReader('')
        daily = reader.calculate_daily_mean(self.wrf_data)
        
        # Convertir a format CSV
        df = pd.DataFrame([daily])
        df.to_csv(filepath, index=False)


def process_wrf_day(
    input_nc: str,
    output_dir: str = '.',
    prefix: str = ''
) -> dict:
    """
    Processa un dia WRF complet
    
    Args:
        input_nc: Fitxer NetCDF d'entrada
        output_dir: Directori de sortida
        prefix: Prefix pels fitxers de sortida
    
    Returns:
        Dict amb paths dels fitxers generats
    """
    import os
    from pathlib import Path
    
    # Llegir dades
    reader = WRFReader(input_nc)
    wrf_data = reader.read()
    
    # Crear directori si cal
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Extreure data del nom
    date = os.path.basename(input_nc).replace('map_', '').replace('.nc', '')
    
    outputs = {}
    
    # Generar sortides
    wg = WRGGenerator(wrf_data)
    wrg_path = os.path.join(output_dir, f'{prefix}wrg_{date}.txt')
    wg.export_wrg_file(wrg_path)
    outputs['wrg'] = wrg_path
    
    # ASCII Grid
    tg = GeoTIFFGenerator(wrf_data)
    asc_path = os.path.join(output_dir, f'{prefix}wind_{date}.asc')
    with open(asc_path, 'w') as f:
        f.write(tg.export_ascii_grid())
    outputs['ascii'] = asc_path
    
    # CSV resum
    csv_path = os.path.join(output_dir, f'{prefix}summary_{date}.csv')
    tg.export_csv_summary()
    with open(csv_path, 'w') as f:
        f.write(tg.export_csv_summary())
    outputs['summary'] = csv_path
    
    # Sèrie temporal
    ts_path = os.path.join(output_dir, f'{prefix}timeseries_{date}.csv')
    tse = TimeSeriesExporter(wrf_data)
    tse.export_full_timeseries(ts_path)
    outputs['timeseries'] = ts_path
    
    # Rosa dels vents
    wr = WRFReader('')
    rose = calculate_windrose(wrf_data)
    
    return {
        'date': date,
        'outputs': outputs,
        'daily_mean': reader.calculate_daily_mean(wrf_data),
        'windrose': rose
    }
