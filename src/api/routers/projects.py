"""
API Router per Projectes i Fitxers

Endpoints:
- POST /projects/create - Crear nou projecte
- POST /projects/save - Guardar projecte
- GET /projects/list - Llistar projectes
- POST /files/upload - Pujar fitxers
- GET /files/list - Llistar fitxers d'un projecte
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, List
import json
from pathlib import Path
from src.core.project_manager import ProjectManager
from src.data.loaders import FileUploader

router = APIRouter(prefix="/projects", tags=["Projects"])

# Instàncies globals
project_manager = ProjectManager()
file_uploader = FileUploader()


class CreateProjectRequest(BaseModel):
    """Request per crear projecte"""
    name: str
    description: str = ""
    author: str = ""


class ProjectResponse(BaseModel):
    """Response de projecte"""
    success: bool
    project: dict = None
    error: str = None


class UploadResponse(BaseModel):
    """Response d'upload"""
    success: bool
    filename: str
    format: str
    metadata: dict = None
    error: str = None


class FileListResponse(BaseModel):
    """Response de llistat de fitxers"""
    files: List[dict]


@router.post("/create", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """
    Crea un nou projecte
    
    Exemple:
    ```json
    {
        "name": "Meu Parc Eòlic",
        "description": "Anàlisi de viabilitat",
        "author": "Oriol"
    }
    ```
    """
    try:
        project = project_manager.create_project(
            name=request.name,
            description=request.description,
            author=request.author
        )
        
        return ProjectResponse(
            success=True,
            project={
                'name': project.config.name,
                'description': project.config.description,
                'created_at': project.config.created_at
            }
        )
    
    except Exception as e:
        return ProjectResponse(success=False, error=str(e))


@router.get("/list")
async def list_projects():
    """
    Llista tots els projectes
    """
    projects = project_manager.list_projects()
    return {"projects": projects}


@router.post("/save", response_model=ProjectResponse)
async def save_project():
    """
    Guarda el projecte actual
    """
    try:
        path = project_manager.save_project()
        return ProjectResponse(
            success=True,
            project={'path': path}
        )
    except Exception as e:
        return ProjectResponse(success=False, error=str(e))


@router.get("/{project_name}", response_model=ProjectResponse)
async def get_project(project_name: str):
    """
    Carrega un projecte existent
    """
    try:
        project = project_manager.load_project(project_name)
        
        return ProjectResponse(
            success=True,
            project={
                'name': project.config.name,
                'description': project.config.description,
                'created_at': project.config.created_at,
                'updated_at': project.config.updated_at,
                'met_sites_count': len(project.met_sites) if project.met_sites else 0,
                'turbines_count': len(project.turbines) if project.turbines else 0,
                'has_topography': project.topography is not None,
                'has_land_cover': project.land_cover is not None
            }
        )
    
    except Exception as e:
        return ProjectResponse(success=False, error=str(e))


@router.delete("/{project_name}", response_model=ProjectResponse)
async def delete_project(project_name: str):
    """
    Elimina un projecte
    """
    success = project_manager.delete_project(project_name)
    
    if success:
        return ProjectResponse(success=True)
    else:
        return ProjectResponse(success=False, error="Project not found")
