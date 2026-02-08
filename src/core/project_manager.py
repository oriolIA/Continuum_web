"""
Project Manager - Full Implementation
Handles project creation, file storage, data association
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class ProjectManager:
    """
    Full project management with persistence
    """
    
    def __init__(self, projects_base: str = "projects"):
        self.projects_base = Path(projects_base)
        self.projects_base.mkdir(parents=True, exist_ok=True)
        logger.info("Project manager initialized", base=str(self.projects_base))
    
    def create_project(self, name: str, description: str = "", author: str = "") -> Dict[str, Any]:
        """
        Create a new project with directory structure
        """
        safe_name = self._sanitize_name(name)
        project_path = self.projects_base / safe_name
        
        if project_path.exists():
            raise ValueError(f"Project '{name}' already exists")
        
        # Create directory structure
        dirs = [
            "",
            "data/met",
            "data/turbines",
            "data/topography",
            "data/landcover",
            "data/results",
            "exports"
        ]
        
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)
        
        # Create project.json
        project_data = {
            "name": name,
            "description": description,
            "author": author,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "2.1.0",
            "status": "active",
            "files": {
                "met": [],
                "turbines": [],
                "topography": [],
                "landcover": [],
                "results": []
            },
            "config": {}
        }
        
        config_path = project_path / "project.json"
        with open(config_path, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        logger.info("Project created", name=name, path=str(project_path))
        
        return project_data
    
    def save_file(self, project_name: str, file_content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Save a file to a project
        """
        safe_name = self._sanitize_name(project_name)
        project_path = self.projects_base / safe_name
        
        if not project_path.exists():
            raise ValueError(f"Project '{project_name}' does not exist")
        
        # Determine subdirectory
        type_map = {
            "met": "data/met",
            "turbines": "data/turbines",
            "topography": "data/topography",
            "landcover": "data/landcover",
            "results": "data/results"
        }
        
        subdir = type_map.get(file_type, "data")
        save_path = project_path / subdir / filename
        
        # Save file
        with open(save_path, 'wb') as f:
            f.write(file_content)
        
        # Update project.json
        config_path = project_path / "project.json"
        with open(config_path, 'r') as f:
            project_data = json.load(f)
        
        project_data["files"][file_type].append({
            "filename": filename,
            "path": str(save_path),
            "type": file_type,
            "uploaded_at": datetime.now().isoformat()
        })
        project_data["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        logger.info("File saved", project=project_name, filename=filename, type=file_type)
        
        return {
            "success": True,
            "filename": filename,
            "path": str(save_path),
            "type": file_type
        }
    
    def get_project(self, name: str) -> Optional[Dict]:
        """
        Load a project
        """
        safe_name = self._sanitize_name(name)
        project_path = self.projects_base / safe_name / "project.json"
        
        if not project_path.exists():
            return None
        
        with open(project_path, 'r') as f:
            return json.load(f)
    
    def list_projects(self) -> list:
        """
        List all projects
        """
        projects = []
        
        for project_path in self.projects_base.iterdir():
            if project_path.is_dir():
                config_path = project_path / "project.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        try:
                            data = json.load(f)
                            projects.append({
                                "name": data.get("name"),
                                "description": data.get("description", ""),
                                "author": data.get("author", ""),
                                "created_at": data.get("created_at", ""),
                                "updated_at": data.get("updated_at", ""),
                                "status": data.get("status", "active"),
                                "path": str(project_path)
                            })
                        except Exception as e:
                            logger.warning("Error loading project", error=str(e))
        
        return sorted(projects, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project
        """
        safe_name = self._sanitize_name(name)
        project_path = self.projects_base / safe_name
        
        if project_path.exists():
            shutil.rmtree(project_path)
            logger.info("Project deleted", name=name)
            return True
        
        return False
    
    def get_files(self, name: str, file_type: str = None) -> list:
        """
        Get files from a project
        """
        project = self.get_project(name)
        if not project:
            return []
        
        if file_type:
            return project.get("files", {}).get(file_type, [])
        
        all_files = []
        for files in project.get("files", {}).values():
            all_files.extend(files)
        
        return all_files
    
    def save_result(self, project_name: str, result_name: str, result_data: dict, result_type: str):
        """
        Save analysis results to a project
        """
        safe_name = self._sanitize_name(project_name)
        project_path = self.projects_base / safe_name / "data/results"
        
        result_path = project_path / f"{result_name}.json"
        
        with open(result_path, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        logger.info("Result saved", project=project_name, result=result_name)
        
        return {"path": str(result_path)}
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for filesystem"""
        return "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
