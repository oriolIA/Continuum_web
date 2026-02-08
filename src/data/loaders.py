"""
Data Loaders - Import/Export per Continuum Web

Suport per:
- NetCDF (.nc)
- GeoTIFF (.tiff, .tif)
- CSV/TXT
- ShapeFiles (.shp)
"""

import io
import zipfile
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd
import xarray as xr
import rasterio
from rasterio.io import MemoryFile
import shapefile
from shapely.geometry import Point, Polygon, box
from shapely import wkt
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LoadedData:
    """Resultat de carregar dades"""
    data: Any
    metadata: Dict[str, Any]
    format: str
    shape: tuple = None
    crs: str = None


class FileUploader:
    """
    Gestor de pujada de fitxers
    
    Suporta:
    - .nc (NetCDF - dades WRF)
    - .tiff/.tif (GeoTIFF - topografia)
    - .csv (dades tabulares)
    - .txt (dades text)
    - .shp (ShapeFiles)
    """
    
    SUPPORTED_FORMATS = {
        '.nc': 'netcdf',
        '.tiff': 'geotiff',
        '.tif': 'geotiff',
        '.csv': 'csv',
        '.txt': 'text',
        '.shp': 'shapefile',
        '.json': 'json'
    }
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def upload_file(self, file_content: bytes, filename: str) -> LoadedData:
        """
        Puja i processa un fitxer
        
        Args:
            file_content: Contingut del fitxer en bytes
            filename: Nom del fitxer
            
        Returns:
            LoadedData amb les dades carregades
        """
        ext = Path(filename).suffix.lower()
        
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Format no suportat: {ext}")
        
        format_type = self.SUPPORTED_FORMATS[ext]
        
        # Guardar fitxer
        filepath = self.upload_dir / filename
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        logger.info("File uploaded", filename=filename, format=format_type)
        
        # Carregar segons el format
        if format_type == 'netcdf':
            return self._load_netcdf(filepath)
        elif format_type == 'geotiff':
            return self._load_geotiff(filepath)
        elif format_type == 'csv':
            return self._load_csv(filepath)
        elif format_type == 'text':
            return self._load_text(filepath)
        elif format_type == 'shapefile':
            return self._load_shapefile(file_content, filepath)
        elif format_type == 'json':
            return self._load_json(filepath)
        
        raise ValueError(f"Format no implementat: {format_type}")
    
    def _load_netcdf(self, filepath: Path) -> LoadedData:
        """Carrega fitxer NetCDF (dades WRF)"""
        with xr.open_dataset(filepath) as ds:
            # Obtenir metadades
            metadata = {
                'dimensions': dict(ds.dims),
                'variables': list(ds.variables.keys()),
                'coords': list(ds.coords.keys())
            }
            
            # Carregar dades principals (primera variable)
            if len(ds.data_vars) > 0:
                first_var = list(ds.data_vars.keys())[0]
                data = ds[first_var].values
                shape = data.shape
            else:
                data = ds
                shape = ()
        
        return LoadedData(
            data=data,
            metadata=metadata,
            format='netcdf',
            shape=shape
        )
    
    def _load_geotiff(self, filepath: Path) -> LoadedData:
        """Carrega GeoTIFF (topografia, land cover)"""
        with rasterio.open(filepath) as src:
            data = src.read(1)  # Primera banda
            
            metadata = {
                'width': src.width,
                'height': src.height,
                'crs': str(src.crs) if src.crs else None,
                'bounds': src.bounds,
                'transform': list(src.transform)[:6],
                'nodata': src.nodata,
                'dtype': str(data.dtype)
            }
        
        return LoadedData(
            data=data,
            metadata=metadata,
            format='geotiff',
            shape=data.shape,
            crs=metadata.get('crs')
        )
    
    def _load_csv(self, filepath: Path) -> LoadedData:
        """Carrega CSV (dades de torres, turbines)"""
        df = pd.read_csv(filepath)
        
        metadata = {
            'columns': list(df.columns),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'rows': len(df),
            'numeric_cols': list(df.select_dtypes(include=[np.number]).columns)
        }
        
        return LoadedData(
            data=df,
            metadata=metadata,
            format='csv',
            shape=(len(df), len(df.columns))
        )
    
    def _load_text(self, filepath: Path) -> LoadedData:
        """Carrega TXT (dades genèriques)"""
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        metadata = {
            'lines': len(lines),
            'first_line': lines[0] if lines else '',
            'last_line': lines[-1] if lines else ''
        }
        
        return LoadedData(
            data=lines,
            metadata=metadata,
            format='text',
            shape=(len(lines),)
        )
    
    def _load_shapefile(self, file_content: bytes, filepath: Path) -> LoadedData:
        """Carrega ShapeFile (.shp)"""
        # Guardar temporalment per carregar
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        # Intentar llegir
        try:
            sf = shapefile.Reader(filepath)
            
            # Convertir a GeoJSON
            features = []
            for rec, shp in zip(sf.records(), sf.shapes()):
                feat = {
                    'type': 'Feature',
                    'properties': dict(zip([f.name for f in sf.fields[1:]], rec)),
                    'geometry': shp.__geo_interface__
                }
                features.append(feat)
            
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            metadata = {
                'n_records': len(sf.records()),
                'fields': [f.name for f in sf.fields[1:]],
                'shape_type': shapefile.SHAPE_TYPE_NAMES.get(sf.shapeType, 'Unknown')
            }
            
            return LoadedData(
                data=geojson,
                metadata=metadata,
                format='shapefile'
            )
            
        except Exception as e:
            logger.error("Shapefile load error", error=str(e))
            raise ValueError(f"Error carregant shapefile: {e}")
    
    def _load_json(self, filepath: Path) -> LoadedData:
        """Carrega JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        metadata = {
            'type': type(data).__name__,
            'keys': list(data.keys()) if isinstance(data, dict) else 'list'
        }
        
        return LoadedData(
            data=data,
            metadata=metadata,
            format='json'
        )


class DataExporter:
    """
    Exporta dades a diversos formats
    """
    
    EXPORT_FORMATS = ['csv', 'json', 'netcdf', 'geotiff']
    
    def export_data(
        self,
        data: Any,
        format: str,
        filepath: str,
        metadata: Dict = None
    ) -> str:
        """
        Exporta dades al format especificat
        """
        format = format.lower()
        
        if format == 'csv':
            return self._export_csv(data, filepath)
        elif format == 'json':
            return self._export_json(data, filepath)
        elif format == 'netcdf':
            return self._export_netcdf(data, filepath)
        elif format == 'geotiff':
            return self._export_geotiff(data, filepath)
        else:
            raise ValueError(f"Format d'export no suportat: {format}")
    
    def _export_csv(self, data: Any, filepath: str) -> str:
        """Exporta a CSV"""
        if isinstance(data, pd.DataFrame):
            data.to_csv(filepath, index=False)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
            df.to_csv(filepath, index=False)
        else:
            raise ValueError("Type not supported for CSV export")
        
        return filepath
    
    def _export_json(self, data: Any, filepath: str) -> str:
        """Exporta a JSON"""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    def _export_netcdf(self, data: Any, filepath: str) -> str:
        """Exporta a NetCDF"""
        if isinstance(data, xr.Dataset):
            data.to_netcdf(filepath)
        elif isinstance(data, np.ndarray):
            # Crear dataset senzill
            ds = xr.Dataset({
                'data': (['x', 'y'], data)
            })
            ds.to_netcdf(filepath)
        else:
            raise ValueError("Type not supported for NetCDF export")
        
        return filepath
    
    def _export_geotiff(self, data: np.ndarray, filepath: str) -> str:
        """Exporta a GeoTIFF"""
        if len(data.shape) != 2:
            raise ValueError("GeoTIFF requires 2D array")
        
        with rasterio.open(
            filepath,
            'w',
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            nodata=-9999
        ) as dst:
            dst.write(data, 1)
        
        return filepath


class TurbineFileParser:
    """
    Parser específic per fitxers de turbines
    
    Formats suportats:
    - CSV amb columnes: name, x, y, hub_height, rotor_diameter
    - TXT format específic
    """
    
    def parse_turbine_file(self, filepath: str) -> pd.DataFrame:
        """
        Carrega fitxer de turbines i retorna DataFrame
        """
        ext = Path(filepath).suffix.lower()
        
        if ext == '.csv':
            df = pd.read_csv(filepath)
        elif ext == '.txt':
            df = self._parse_txt(filepath)
        else:
            raise ValueError(f"Format no suportat: {ext}")
        
        # Validar columns requerides
        required = ['name', 'x', 'y']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Columnes manquants: {missing}")
        
        return df
    
    def _parse_txt(self, filepath: str) -> pd.DataFrame:
        """Parseja TXT amb format específic de turbines"""
        data = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    data.append({
                        'name': parts[0],
                        'x': float(parts[1]),
                        'y': float(parts[2]),
                        'hub_height': float(parts[3]) if len(parts) > 3 else 80,
                        'rotor_diameter': float(parts[4]) if len(parts) > 4 else 100
                    })
        
        return pd.DataFrame(data)


class MetDataParser:
    """
    Parser per dades meteorològiques
    
    Formats:
    - CSV amb: timestamp, wind_speed, wind_direction, temperature, pressure, etc.
    - NetCDF (dades WRF)
    """
    
    def parse_met_file(self, filepath: str) -> pd.DataFrame:
        """Carrega dades meteorològiques"""
        ext = Path(filepath).suffix.lower()
        
        if ext == '.nc':
            return self._parse_netcdf(filepath)
        elif ext == '.csv':
            return self._parse_csv(filepath)
        else:
            raise ValueError(f"Format no suportat: {ext}")
    
    def _parse_csv(self, filepath: str) -> pd.DataFrame:
        """Parseja CSV meteorològic"""
        df = pd.read_csv(filepath)
        
        # Convertir timestamp si existeix
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def _parse_netcdf(self, filepath: str) -> pd.DataFrame:
        """Parseja NetCDF i retorna DataFrame"""
        with xr.open_dataset(filepath) as ds:
            # Extreure variables principals
            data = {}
            
            for var in ['U', 'V', 'W', 'T', 'P']:
                if var in ds.variables:
                    data[var.lower()] = ds[var].values.flatten()
            
            # Crear DataFrame
            df = pd.DataFrame(data)
            
            # Afegir coordenades temporals si existeixen
            if 'time' in ds.coords:
                df['timestamp'] = ds['time'].values
        
        return df
