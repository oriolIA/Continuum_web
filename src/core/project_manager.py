"""
Project Manager - Gestió de projectes Continuum

Funcionalitats:
- Crear nous projectes
- Guardar/carregar projectes
- Exportar resultats
"""

import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ProjectConfig:
    """Configuració del projecte"""
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    version: str = "2.0.0"
    author: str = ""
    crs: str = "EPSG:4326"  # WGS84 per defecte


@dataclass
class ProjectData:
    """Dades del projecte"""
    config: ProjectConfig
    met_sites: list = None
    turbines: list = None
    topography: Dict = None
    land_cover: Dict = None
    wind_rose: Dict = None
    results: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            'config': asdict(self.config),
            'met_sites': self.met_sites,
            'turbines': self.turbines,
            'topography': self.topography,
            'land_cover': self.land_cover,
            'wind_rose': self.wind_rose,
            'results': self.results
        }


class ProjectManager:
    """
    Gestiona projectes de Continuum
    
    Estructura d'un projecte:
    project/
    ├── project.json          # Configuració
    ├── data/
    │   ├── met/             # Dades meteorològiques
    │   ├── turbines/        # Fitxers de turbines
    │   ├── topography/      # Dades topogràfiques
    │   └── results/        # Resultats de càlculs
    └── exports/             # Exportacions
    """
    
    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.current_project: Optional[ProjectData] = None
    
    def create_project(
        self,
        name: str,
        description: str = "",
        author: str = ""
    ) -> ProjectData:
        """
        Crea un nou projecte
        
        Args:
            name: Nom del projecte
            description: Descripció
            author: Autor
            
        Returns:
            ProjectData amb el projecte creat
        """
        # Netejar nom per usar com a carpeta
        safe_name = self._sanitize_name(name)
        
        # Crear directori
        project_dir = self.projects_dir / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectoris
        (project_dir / "data").mkdir(exist_ok=True)
        (project_dir / "data/met").mkdir(exist_ok=True)
        (project_dir / "data/turbines").mkdir(exist_ok=True)
        (project_dir / "data/topography").mkdir(exist_ok=True)
        (project_dir / "data/results").mkdir(exist_ok=True)
        (project_dir / "exports").mkdir(exist_ok=True)
        
        # Configuració
        config = ProjectConfig(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            author=author
        )
        
        # Crear projecte
        self.current_project = ProjectData(
            config=config,
            met_sites=[],
            turbines=[],
            topography=None,
            land_cover=None,
            wind_rose=None,
            results={}
        )
        
        # Guardar config
        self._save_config(project_dir, config)
        
        logger.info("Project created", name=name, path=str(project_dir))
        
        return self.current_project
    
    def save_project(self, project: ProjectData = None) -> str:
        """
        Guarda el projecte actual
        
        Args:
            project: Projecte a guardar (current si és None)
            
        Returns:
            Path del projecte guardat
        """
        if project is None:
            project = self.current_project
        
        if project is None:
            raise ValueError("No project to save")
        
        safe_name = self._sanitize_name(project.config.name)
        project_dir = self.projects_dir / safe_name
        
        # Actualitzar timestamp
        project.config.updated_at = datetime.now().isoformat()
        
        # Guardar config
        self._save_config(project_dir, project.config)
        
        # Guardar dades
        self._save_project_data(project_dir, project)
        
        logger.info("Project saved", name=project.config.name, path=str(project_dir))
        
        return str(project_dir)
    
    def load_project(self, name: str) -> ProjectData:
        """
        Carrega un projecte existent
        
        Args:
            name: Nom del projecte
            
        Returns:
            ProjectData carregat
        """
        safe_name = self._sanitize_name(name)
        project_dir = self.projects_dir / safe_name
        
        if not project_dir.exists():
            raise ValueError(f"Project not found: {name}")
        
        # Carregar config
        config = self._load_config(project_dir)
        
        # Carregar dades
        project = self._load_project_data(project_dir, config)
        
        self.current_project = project
        
        logger.info("Project loaded", name=name)
        
        return project
    
    def list_projects(self) -> list:
        """
        Llista tots els projectes
        """
        projects = []
        
        for item in self.projects_dir.iterdir():
            if item.is_dir():
                config_path = item / "project.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        projects.append({
                            'name': config['name'],
                            'description': config.get('description', ''),
                            'created_at': config.get('created_at', ''),
                            'updated_at': config.get('updated_at', ''),
                            'path': str(item)
                        })
                    except Exception as e:
                        logger.warning("Error loading project config", error=str(e))
        
        return sorted(projects, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    def delete_project(self, name: str) -> bool:
        """
        Elimina un projecte
        """
        safe_name = self._sanitize_name(name)
        project_dir = self.projects_dir / safe_name
        
        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.info("Project deleted", name=name)
            return True
        
        return False
    
    def export_project(
        self,
        project: ProjectData = None,
        format: str = "zip",
        output_path: str = None
    ) -> str:
        """
        Exporta el projecte a ZIP
        
        Args:
            project: Projecte a exportar
            format: Format d'export (només ZIP ara)
            output_path: Path de sortida
            
        Returns:
            Path del fitxer exportat
        """
        if project is None:
            project = self.current_project
        
        if project is None:
            raise ValueError("No project to export")
        
        safe_name = self._sanitize_name(project.config.name)
        
        if output_path is None:
            output_path = str(self.projects_dir / f"{safe_name}.zip")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Afegir project.json
            config_data = json.dumps(project.to_dict(), indent=2)
            zipf.writestr("project.json", config_data)
            
            # Afegir directoris de dades
            project_dir = self.projects_dir / safe_name
            
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(project_dir))
                    zipf.write(file_path, arcname)
        
        logger.info("Project exported", name=project.config.name, path=output_path)
        
        return output_path
    
    def import_project(self, filepath: str) -> ProjectData:
        """
        Importa un projecte des de ZIP
        
        Args:
            filepath: Path del fitxer ZIP
            
        Returns:
            ProjectData importat
        """
        filepath = Path(filepath)
        temp_dir = self.projects_dir / "import_temp"
        
        # Extraure
        with zipfile.ZipFile(filepath, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # Carregar
        project = self.load_project(temp_dir.name)
        
        # Moure a ubicació final
        safe_name = self._sanitize_name(project.config.name)
        final_dir = self.projects_dir / safe_name
        
        if final_dir.exists():
            shutil.rmtree(final_dir)
        
        shutil.move(str(temp_dir), str(final_dir))
        
        # Recarregar
        project = self.load_project(safe_name)
        
        logger.info("Project imported", name=project.config.name)
        
        return project
    
    def _sanitize_name(self, name: str) -> str:
        """Neteja el nom per usar com a carpeta"""
        return "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
    
    def _save_config(self, project_dir: Path, config: ProjectConfig):
        """Guarda la configuració"""
        config_path = project_dir / "project.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2)
    
    def _load_config(self, project_dir: Path) -> ProjectConfig:
        """Carrega la configuració"""
        config_path = project_dir / "project.json"
        with open(config_path, 'r') as f:
            data = json.load(f)
        return ProjectConfig(**data)
    
    def _save_project_data(self, project_dir: Path, project: ProjectData):
        """Guarda les dades del projecte"""
        # Guardar JSON principal amb metadades
        data = project.to_dict()
        
        # Guardar a project.json (sobrescriu amb dades completes)
        with open(project_dir / "project.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_project_data(self, project_dir: Path, config: ProjectConfig) -> ProjectData:
        """Carrega les dades del projecte"""
        # Carregar project.json
        with open(project_dir / "project.json", 'r') as f:
            data = json.load(f)
        
        return ProjectData(
            config=config,
            met_sites=data.get('met_sites', []),
            turbines=data.get('turbines', []),
            topography=data.get('topography'),
            land_cover=data.get('land_cover'),
            wind_rose=data.get('wind_rose'),
            results=data.get('results', {})
        )


# Import os per walk
import os
