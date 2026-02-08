"""
API Router per Upload de Fitxers

Endpoints:
- POST /files/upload - Pujar un fitxer
- POST /files/upload-multiple - Pujar múltiples fitxers
- GET /files/list - Llistar fitxers
- GET /files/download - Descarregar fitxer
- DELETE /files/delete - Eliminar fitxer
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, List
import json
from pathlib import Path
from src.data.loaders import FileUploader

router = APIRouter(prefix="/files", tags=["Files"])

# Instància global
file_uploader = FileUploader()


class UploadResponse(BaseModel):
    """Response d'upload"""
    success: bool
    filename: str
    format: str
    metadata: dict = None
    error: str = None


class FileInfo(BaseModel):
    """Informació d'un fitxer"""
    name: str
    format: str
    size: int
    path: str
    metadata: dict = None


class FileListResponse(BaseModel):
    """Response de llistat"""
    files: List[FileInfo]


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...)
):
    """
    Puja un fitxer
    
    Parameters:
    - file: El fitxer a pujar
    - project: Nom del projecte
    
    Formats suportats:
    - .nc (NetCDF)
    - .tiff/.tif (GeoTIFF)
    - .csv (dades tabulares)
    - .txt (text)
    - .shp (ShapeFiles)
    """
    try:
        # Llegir contingut
        content = await file.read()
        
        # Pujar
        result = file_uploader.upload_file(content, file.filename)
        
        # Moure al directori del projecte
        project_dir = Path("projects") / project / "data"
        if project_dir.exists():
            dest = project_dir / file.filename
            with open(dest, 'wb') as f:
                f.write(content)
        
        return UploadResponse(
            success=True,
            filename=file.filename,
            format=result.format,
            metadata=result.metadata
        )
    
    except Exception as e:
        return UploadResponse(success=False, filename=file.filename, error=str(e))


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    project: str = Form(...)
):
    """
    Puja múltiples fitxers simultàniament
    """
    results = []
    
    for file in files:
        try:
            content = await file.read()
            result = file_uploader.upload_file(content, file.filename)
            
            results.append({
                'filename': file.filename,
                'success': True,
                'format': result.format,
                'metadata': result.metadata
            })
        except Exception as e:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })
    
    return {'files': results}


@router.get("/list", response_model=FileListResponse)
async def list_files(project: str, filetype: str = None):
    """
    Llista els fitxers d'un projecte
    
    Query params:
    - project: Nom del projecte
    - filetype: Filtre per tipus (netcdf, geotiff, csv, etc.)
    """
    project_dir = Path("projects") / project / "data"
    
    if not project_dir.exists():
        return FileListResponse(files=[])
    
    files = []
    
    for filepath in project_dir.rglob("*"):
        if filepath.is_file():
            # Filtrar per tipus si cal
            if filetype:
                if filepath.suffix.lower() != f".{filetype}":
                    continue
            
            files.append(FileInfo(
                name=filepath.name,
                format=filepath.suffix.lower().replace('.', ''),
                size=filepath.stat().st_size,
                path=str(filepath.relative_to(project_dir.parent)),
                metadata=None
            ))
    
    return FileListResponse(files=files)


@router.delete("/delete")
async def delete_file(project: str, filename: str):
    """
    Elimina un fitxer
    """
    filepath = Path("projects") / project / "data" / filename
    
    if filepath.exists():
        filepath.unlink()
        return {'success': True, 'filename': filename}
    else:
        return {'success': False, 'error': 'File not found'}


@router.get("/download/{project}/{filename}")
async def download_file(project: str, filename: str):
    """
    Descarrega un fitxer
    """
    filepath = Path("projects") / project / "data" / filename
    
    if filepath.exists():
        return FileResponse(str(filepath))
    else:
        raise HTTPException(status_code=404, detail="File not found")


# Import necessari
from fastapi.responses import FileResponse
