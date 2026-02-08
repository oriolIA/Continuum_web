"""
File Upload API - Working Implementation
Actually saves files to disk and associates with projects
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, List
import json
from pathlib import Path
from src.core.project_manager import ProjectManager

router = APIRouter(prefix="/files", tags=["Files"])

# Global project manager
project_manager = ProjectManager()


class UploadResponse(BaseModel):
    """Upload response"""
    success: bool
    filename: str
    type: str
    project: str
    path: str = None
    error: str = None


class FileListItem(BaseModel):
    """File info"""
    filename: str
    type: str
    uploaded_at: str = None


class FileListResponse(BaseModel):
    """List files response"""
    project: str
    files: List[FileListItem]


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    file_type: str = Form("met")
):
    """
    Upload a file to a project
    - file: The file to upload
    - project: Project name
    - file_type: met, turbines, topography, landcover
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save file
        result = project_manager.save_file(
            project_name=project,
            file_content=content,
            filename=file.filename,
            file_type=file_type
        )
        
        return UploadResponse(
            success=True,
            filename=file.filename,
            type=file_type,
            project=project,
            path=result.get("path")
        )
    
    except Exception as e:
        return UploadResponse(
            success=False,
            filename=file.filename,
            type=file_type,
            project=project,
            error=str(e)
        )


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    project: str = Form(...),
    file_type: str = Form("met")
):
    """
    Upload multiple files to a project
    """
    results = []
    
    for file in files:
        try:
            content = await file.read()
            result = project_manager.save_file(
                project_name=project,
                file_content=content,
                filename=file.filename,
                file_type=file_type
            )
            results.append({
                "filename": file.filename,
                "success": True,
                "type": file_type
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}


@router.get("/list", response_model=FileListResponse)
async def list_files(project: str, file_type: str = None):
    """
    List files in a project
    """
    files = project_manager.get_files(project, file_type)
    
    return FileListResponse(
        project=project,
        files=[
            FileListItem(
                filename=f.get("filename", ""),
                type=f.get("type", ""),
                uploaded_at=f.get("uploaded_at", "")
            )
            for f in files
        ]
    )


@router.delete("/delete")
async def delete_file(project: str, filename: str, file_type: str = Form(...)):
    """
    Delete a file from a project
    """
    # Get project config
    project_data = project_manager.get_project(project)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find and delete file
    files = project_data.get("files", {}).get(file_type, [])
    for f in files:
        if f.get("filename") == filename:
            file_path = Path(f.get("path", ""))
            if file_path.exists():
                file_path.unlink()
            
            # Update project.json
            project_data["files"][file_type].remove(f)
            config_path = Path(projects_base) / project / "project.json"
            with open(config_path, 'w') as f:
                json.dump(project_data, f)
            
            return {"success": True, "filename": filename}
    
    raise HTTPException(status_code=404, detail="File not found")


# Global for delete endpoint
from src.core.project_manager import projects_base
