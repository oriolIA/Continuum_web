"""
Projects API - Working Implementation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from src.core.project_manager import ProjectManager

router = APIRouter(prefix="/projects", tags=["Projects"])

# Global project manager
project_manager = ProjectManager()


class CreateProjectRequest(BaseModel):
    """Create project request"""
    name: str
    description: str = ""
    author: str = ""


class ProjectInfo(BaseModel):
    """Project info response"""
    name: str
    description: str = ""
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "active"
    path: str = ""
    files_count: int = 0


class ProjectResponse(BaseModel):
    """General response"""
    success: bool
    message: str = ""
    project: ProjectInfo = None


@router.post("/create", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """
    Create a new project
    """
    try:
        # Create project
        project_data = project_manager.create_project(
            name=request.name,
            description=request.description,
            author=request.author
        )
        
        return ProjectResponse(
            success=True,
            message=f"Project '{request.name}' created successfully",
            project=ProjectInfo(
                name=project_data["name"],
                description=project_data.get("description", ""),
                author=project_data.get("author", ""),
                created_at=project_data["created_at"],
                updated_at=project_data["updated_at"],
                status=project_data["status"],
                path=str(project_manager.projects_base / request.name.replace(" ", "_"))
            )
        )
    
    except ValueError as e:
        return ProjectResponse(
            success=False,
            message=str(e)
        )
    except Exception as e:
        return ProjectResponse(
            success=False,
            message=f"Error creating project: {str(e)}"
        )


@router.get("/list", response_model=List[ProjectInfo])
async def list_projects():
    """
    List all projects
    """
    return project_manager.list_projects()


@router.get("/{project_name}", response_model=ProjectResponse)
async def get_project(project_name: str):
    """
    Get project details
    """
    project_data = project_manager.get_project(project_name)
    
    if not project_data:
        return ProjectResponse(
            success=False,
            message=f"Project '{project_name}' not found"
        )
    
    # Count files
    files_count = sum(len(files) for files in project_data.get("files", {}).values())
    
    return ProjectResponse(
        success=True,
        project=ProjectInfo(
            name=project_data["name"],
            description=project_data.get("description", ""),
            author=project_data.get("author", ""),
            created_at=project_data["created_at"],
            updated_at=project_data["updated_at"],
            status=project_data.get("status", "active"),
            path=str(project_manager.projects_base / project_name.replace(" ", "_")),
            files_count=files_count
        )
    )


@router.delete("/{project_name}", response_model=ProjectResponse)
async def delete_project(project_name: str):
    """
    Delete a project
    """
    success = project_manager.delete_project(project_name)
    
    if success:
        return ProjectResponse(
            success=True,
            message=f"Project '{project_name}' deleted"
        )
    else:
        return ProjectResponse(
            success=False,
            message=f"Project '{project_name}' not found"
        )
