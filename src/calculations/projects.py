"""
Project Management per Continuum

Sistema de projectes per gestionar:
- Àrees d'estudi
- Fitxers carregats (WRG, TIFF, series)
- Metadades i estadístiques
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import pandas as pd
import numpy as np


@dataclass
class Project:
    """Projecte d'estudi eòlic"""
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    # Dades carregades
    wrg_data: Optional[Dict] = None
    wrg_filepath: Optional[str] = None
    wind_field: Optional[np.ndarray] = None
    latitude: Optional[np.ndarray] = None
    longitude: Optional[np.ndarray] = None
    
    # Sèries temporals
    timeseries_data: Optional[pd.DataFrame] = None
    timeseries_filepath: Optional[str] = None
    
    # Referència WRF
    wrf_reference: Optional[str] = None
    
    # Turbines del projecte
    turbines: List[Dict] = field(default_factory=list)
    
    # Layout
    layout: Optional[List[Dict]] = None
    
    # Metadades
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectManager:
    """
    Gestor de projectes Continuum
    
    Permet:
    - Crear projectes nous
    - Carregar dades (WRG, TIFF, CSV)
    - Emmagatzemar estadístiques
    - Exportar/importar projectes
    """
    
    def __init__(self, projects_dir: str = "./projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(exist_ok=True)
        self.current_project: Optional[Project] = None
    
    def create_project(self, name: str, description: str = "") -> Project:
        """Crea un nou projecte"""
        from datetime import datetime
        
        project = Project(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.current_project = project
        return project
    
    def load_wrg(self, filepath: str) -> dict:
        """
        Carrega un fitxer WRG
        
        Args:
            filepath: Path al fitxer WRG
        
        Returns:
            Resum de les dades carregades
        """
        if self.current_project is None:
            raise ValueError("No project selected. Create or load a project first.")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parsejar WRG
        data = self._parse_wrg(content)
        
        self.current_project.wrg_filepath = filepath
        self.current_project.wrg_data = data
        
        # Actualitzar metadades
        self.current_project.updated_at = str(pd.Timestamp.now())
        
        return data
    
    def _parse_wrg(self, content: str) -> dict:
        """Parseja un fitxer WRG"""
        lines = content.strip().split('\n')
        data = {}
        current_var = None
        matrix = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key in ['nrows', 'ncols', 'cellsize']:
                    data[key] = int(value)
                elif key in ['xllcorner', 'yllcorner']:
                    data[key] = float(value)
                elif key == 'variable':
                    current_var = value
                    matrix = []
                    data[current_var] = {
                        'unit': lines[i + 1].replace('UNIT', '').strip() if i + 1 < len(lines) else '',
                        'values': []
                    }
                elif key == 'unit' and current_var:
                    data[current_var]['unit'] = value
            elif current_var and line and not line.replace('.', '').replace('-', '').isdigit() == line:
                # És una línia de dades
                try:
                    values = [float(x) for x in line.split()]
                    matrix.extend(values)
                except:
                    pass
            elif current_var and line and all(c in ' -+.0123456789' for c in line):
                # És una línia de dades
                try:
                    values = [float(x) for x in line.split()]
                    matrix.extend(values)
                except:
                    pass
            
            i += 1
        
        # Guardar matriu
        if 'wind_speed' in data and matrix:
            nrows = data.get('nrows', int(np.sqrt(len(matrix))))
            ncols = data.get('ncols', nrows)
            data['wind_speed']['matrix'] = np.array(matrix).reshape(nrows, ncols)
        
        return data
    
    def load_ascii_grid(self, filepath: str) -> dict:
        """
        Carrega un fitxer ASCII Grid
        
        Args:
            filepath: Path al fitxer ASC
        
        Returns:
            Resum de les dades carregades
        """
        if self.current_project is None:
            raise ValueError("No project selected.")
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Parsejar header
        header = {}
        data_start = 0
        
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if parts[0].lower() in ['ncols', 'nrows', 'cellsize', 'xllcorner', 'yllcorner', 'nodata_value']:
                header[parts[0].lower()] = float(parts[1]) if parts[0].lower() != 'ncols' and parts[0].lower() != 'nrows' else int(parts[1])
            else:
                data_start = i
                break
        
        # Llegir dades
        data_matrix = []
        for line in lines[data_start:]:
            values = [float(x) for x in line.strip().split()]
            data_matrix.extend(values)
        
        data_matrix = np.array(data_matrix).reshape(header['nrows'], header['ncols'])
        
        # Guardar al projecte
        self.current_project.wind_field = data_matrix
        self.current_project.metadata['ascii_grid'] = header
        
        return {
            'header': header,
            'shape': data_matrix.shape,
            'min': float(np.nanmin(data_matrix)),
            'max': float(np.nanmax(data_matrix)),
            'mean': float(np.nanmean(data_matrix))
        }
    
    def load_timeseries(self, filepath: str, time_col: str = None, 
                       speed_col: str = 'wind_speed', direction_col: str = 'wind_direction') -> dict:
        """
        Carrega una sèrie temporal
        
        Args:
            filepath: Path al fitxer CSV/TXT
            time_col: Columna de temps (opcional)
            speed_col: Columna de velocitat
            direction_col: Columna de direcció
        """
        if self.current_project is None:
            raise ValueError("No project selected.")
        
        # Detectar format
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_csv(filepath, delim_whitespace=True)
        
        # Validar columnes
        if speed_col not in df.columns:
            raise ValueError(f"Column '{speed_col}' not found. Available: {list(df.columns)}")
        
        # Guardar
        self.current_project.timeseries_filepath = filepath
        self.current_project.timeseries_data = df
        
        # Calcular estadístiques bàsiques
        stats = {
            'n_samples': len(df),
            'speed_mean': float(df[speed_col].mean()),
            'speed_std': float(df[speed_col].std()),
            'speed_min': float(df[speed_col].min()),
            'speed_max': float(df[speed_col].max()),
            'columns': list(df.columns)
        }
        
        if direction_col in df.columns:
            stats['direction_mean'] = float(df[direction_col].mean())
        
        if time_col and time_col in df.columns:
            stats['time_range'] = {
                'start': str(df[time_col].iloc[0]),
                'end': str(df[time_col].iloc[-1])
            }
        
        return stats
    
    def extract_point_from_field(
        self,
        lat: float,
        lon: float
    ) -> dict:
        """
        Extreu valor en un punt del camp de vent
        
        Args:
            lat: Latitud
            lon: Longitud
        """
        if self.current_project is None:
            raise ValueError("No project selected.")
        
        if self.current_project.wind_field is None:
            raise ValueError("No wind field loaded.")
        
        field = self.current_project.wind_field
        lat_arr = self.current_project.latitude
        lon_arr = self.current_project.longitude
        
        # Trobar índex més proper
        lat_idx = np.abs(lat_arr[:, 0] - lat).argmin()
        lon_idx = np.abs(lon_arr[0, :] - lon).argmin()
        
        value = field[lat_idx, lon_idx]
        
        return {
            'latitude': lat,
            'longitude': lon,
            'lat_idx': int(lat_idx),
            'lon_idx': int(lon_idx),
            'wind_speed': float(value),
            'coordinates_match': (lat_arr[lat_idx, lon_idx], lon_arr[lat_idx, lon_idx])
        }
    
    def add_turbine(self, turbine_config: dict) -> dict:
        """
        Afegeix una turbina al projecte
        
        Args:
            turbine_config: Dict amb name, x, y, model
        """
        if self.current_project is None:
            raise ValueError("No project selected.")
        
        self.current_project.turbines.append(turbine_config)
        return turbine_config
    
    def set_layout(self, layout: List[Dict]) -> List[Dict]:
        """
        Defineix el layout del parc
        
        Args:
            layout: Llista de diccionaris amb x, y
        """
        if self.current_project is None:
            raise ValueError("No project selected.")
        
        self.current_project.layout = layout
        return layout
    
    def get_project_summary(self) -> dict:
        """Retorna resum del projecte actual"""
        if self.current_project is None:
            return {"error": "No project loaded"}
        
        p = self.current_project
        
        return {
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "has_wrg": p.wrg_data is not None,
            "has_wind_field": p.wind_field is not None,
            "has_timeseries": p.timeseries_data is not None,
            "n_turbines": len(p.turbines),
            "has_layout": p.layout is not None,
            "files": {
                "wrg": p.wrg_filepath,
                "timeseries": p.timeseries_filepath,
                "wrf_reference": p.wrf_reference
            }
        }
    
    def export_project(self, filepath: str):
        """Exporta el projecte a JSON"""
        if self.current_project is None:
            raise ValueError("No project to export")
        
        data = {
            'name': self.current_project.name,
            'description': self.current_project.description,
            'created_at': self.current_project.created_at,
            'updated_at': self.current_project.updated_at,
            'turbines': self.current_project.turbines,
            'layout': self.current_project.layout,
            'metadata': self.current_project.metadata
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_project(self, filepath: str) -> Project:
        """Carrega un projecte des de JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            turbines=data.get('turbines', []),
            layout=data.get('layout'),
            metadata=data.get('metadata', {})
        )
        
        self.current_project = project
        return project
    
    def clear_project(self):
        """Neteja el projecte actual"""
        self.current_project = None
