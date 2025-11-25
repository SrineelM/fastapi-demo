"""
File Upload and Form Handling Routes Module

Demonstrates:
- File uploads using File and UploadFile
- Multipart form data handling
- Multiple file uploads
- Form validation and metadata extraction
- File content processing

This module provides comprehensive file handling patterns for the FastAPI application.
"""

import os
import shutil
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

# Create router
files_router = APIRouter(prefix="/files", tags=["File Upload & Forms"])

# Upload directory configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".jpg", ".jpeg", ".png", ".csv", ".json"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ==================== PYDANTIC MODELS ====================

class FileResponse(BaseModel):
    """File upload response model"""
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Stored file path")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")


class MultiFileResponse(BaseModel):
    """Multiple file upload response"""
    files: List[FileResponse] = Field(..., description="List of uploaded files")
    total_size: int = Field(..., description="Total size of all files")
    count: int = Field(..., description="Number of files uploaded")


class DocumentMetadata(BaseModel):
    """Document metadata for form submission"""
    title: str = Field(..., max_length=200, description="Document title")
    description: str | None = Field(None, description="Document description")
    tags: list[str] = Field(default_factory=list, description="Document tags")
    is_public: bool = Field(default=False, description="Public visibility")


class UserProfileUpdate(BaseModel):
    """User profile update with file upload"""
    username: str = Field(..., min_length=3, max_length=50)
    bio: str | None = Field(None, max_length=500)
    age: int | None = Field(None, ge=18, le=120)


# ==================== UTILITY FUNCTIONS ====================

def validate_file(file: UploadFile, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        max_size: Maximum file size in bytes
        
    Raises:
        HTTPException: If file validation fails
    """
    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {allowed}"
        )
    
    # Check file size
    if file.size and file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {max_mb}MB limit"
        )


async def save_upload_file(file: UploadFile, directory: Path = UPLOAD_DIR) -> str:
    """
    Save uploaded file to disk
    
    Args:
        file: Uploaded file
        directory: Directory to save file
        
    Returns:
        Path to saved file
    """
    # Create unique filename
    file_path = directory / file.filename
    
    try:
        # Save file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info("File saved", filename=file.filename, path=str(file_path))
        return str(file_path)
        
    except Exception as e:
        logger.error("File save error", filename=file.filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0


# ==================== ENDPOINTS ====================

@files_router.post(
    "/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload single file",
    description="Upload a single file with validation"
)
async def upload_single_file(
    file: Annotated[UploadFile, File(description="File to upload")]
) -> FileResponse:
    """
    Upload a single file.
    
    Supports: .txt, .pdf, .jpg, .jpeg, .png, .csv, .json
    Max size: 10MB
    
    Args:
        file: File to upload
        
    Returns:
        File metadata including path and size
        
    Raises:
        HTTPException: If file validation fails
    """
    # Validate file
    validate_file(file)
    
    # Save file
    file_path = await save_upload_file(file)
    file_size = get_file_size(file_path)
    
    logger.info("File uploaded", filename=file.filename, size=file_size)
    
    return FileResponse(
        filename=file.filename,
        file_path=file_path,
        size=file_size,
        content_type=file.content_type or "application/octet-stream"
    )


@files_router.post(
    "/upload-multiple",
    response_model=MultiFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple files",
    description="Upload multiple files at once"
)
async def upload_multiple_files(
    files: Annotated[
        List[UploadFile],
        File(description="Multiple files to upload")
    ]
) -> MultiFileResponse:
    """
    Upload multiple files at once.
    
    Args:
        files: List of files to upload
        
    Returns:
        Information about all uploaded files
        
    Raises:
        HTTPException: If any file validation fails
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    uploaded_files: List[FileResponse] = []
    total_size = 0
    
    for file in files:
        # Validate and save
        validate_file(file)
        file_path = await save_upload_file(file)
        file_size = get_file_size(file_path)
        total_size += file_size
        
        uploaded_files.append(
            FileResponse(
                filename=file.filename,
                file_path=file_path,
                size=file_size,
                content_type=file.content_type or "application/octet-stream"
            )
        )
    
    logger.info("Multiple files uploaded", count=len(files), total_size=total_size)
    
    return MultiFileResponse(
        files=uploaded_files,
        total_size=total_size,
        count=len(uploaded_files)
    )


@files_router.post(
    "/upload-with-metadata",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file with metadata",
    description="Upload file along with metadata in multipart form"
)
async def upload_with_metadata(
    file: Annotated[UploadFile, File(description="File to upload")],
    title: Annotated[str, Form(description="Document title")],
    description: Annotated[str | None, Form()] = None,
    tags: Annotated[list[str] | None, Form()] = None,
    is_public: Annotated[bool, Form()] = False
) -> dict:
    """
    Upload file with metadata.
    
    Demonstrates combining file upload with form data.
    
    Args:
        file: File to upload
        title: Document title (required)
        description: Document description (optional)
        tags: Document tags (optional)
        is_public: Public visibility flag (optional)
        
    Returns:
        Upload result with file and metadata info
    """
    # Validate file
    validate_file(file)
    
    # Save file
    file_path = await save_upload_file(file)
    file_size = get_file_size(file_path)
    
    logger.info(
        "File with metadata uploaded",
        filename=file.filename,
        title=title,
        tags=tags or []
    )
    
    return {
        "message": "File uploaded successfully with metadata",
        "file": {
            "filename": file.filename,
            "path": file_path,
            "size": file_size,
            "content_type": file.content_type
        },
        "metadata": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "is_public": is_public
        }
    }


@files_router.post(
    "/upload-profile",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload profile picture",
    description="Upload profile picture with user profile form data"
)
async def upload_profile_picture(
    profile_picture: Annotated[
        UploadFile,
        File(description="Profile picture (JPG, PNG)")
    ],
    username: Annotated[str, Form(min_length=3, max_length=50)],
    bio: Annotated[str | None, Form(max_length=500)] = None,
    age: Annotated[int | None, Form(ge=18, le=120)] = None
) -> dict:
    """
    Upload profile picture with user profile data.
    
    Demonstrates form data validation with Pydantic-like constraints.
    
    Args:
        profile_picture: Profile image file
        username: Username
        bio: User bio
        age: User age
        
    Returns:
        Profile update result
    """
    # Validate image file
    if profile_picture.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are allowed"
        )
    
    validate_file(profile_picture)
    
    # Save file
    file_path = await save_upload_file(profile_picture)
    file_size = get_file_size(file_path)
    
    logger.info(
        "Profile picture uploaded",
        username=username,
        picture_size=file_size
    )
    
    return {
        "message": "Profile updated successfully",
        "profile": {
            "username": username,
            "bio": bio,
            "age": age,
            "profile_picture": {
                "filename": profile_picture.filename,
                "path": file_path,
                "size": file_size,
                "content_type": profile_picture.content_type
            }
        }
    }


@files_router.post(
    "/upload-documents",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple documents",
    description="Upload multiple documents with metadata"
)
async def upload_documents(
    documents: Annotated[
        List[UploadFile],
        File(description="Multiple documents")
    ],
    category: Annotated[str, Form(description="Document category")],
    priority: Annotated[str, Form(description="Priority level")] = "normal"
) -> dict:
    """
    Upload multiple documents with category metadata.
    
    Args:
        documents: List of document files
        category: Document category
        priority: Priority level
        
    Returns:
        Upload result with all documents
    """
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document is required"
        )
    
    uploaded_docs = []
    total_size = 0
    
    for doc in documents:
        validate_file(doc)
        file_path = await save_upload_file(doc)
        file_size = get_file_size(file_path)
        total_size += file_size
        
        uploaded_docs.append({
            "filename": doc.filename,
            "path": file_path,
            "size": file_size
        })
    
    logger.info(
        "Documents uploaded",
        count=len(uploaded_docs),
        category=category,
        priority=priority
    )
    
    return {
        "message": "Documents uploaded successfully",
        "metadata": {
            "category": category,
            "priority": priority
        },
        "documents": uploaded_docs,
        "total_size": total_size
    }


@files_router.get(
    "/list",
    summary="List uploaded files",
    description="List all files in upload directory"
)
async def list_files() -> dict:
    """
    List all uploaded files.
    
    Returns:
        List of files with their metadata
    """
    files = []
    
    try:
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "created": file_path.stat().st_ctime
                })
    except Exception as e:
        logger.error("Error listing files", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )
    
    return {
        "total": len(files),
        "files": files
    }


@files_router.delete(
    "/delete/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete uploaded file",
    description="Delete a specific uploaded file"
)
async def delete_file(filename: str) -> None:
    """
    Delete an uploaded file.
    
    Args:
        filename: Name of file to delete
        
    Raises:
        HTTPException: If file not found or deletion fails
    """
    file_path = UPLOAD_DIR / filename
    
    # Prevent path traversal attacks
    if not file_path.parent == UPLOAD_DIR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {filename} not found"
        )
    
    try:
        file_path.unlink()
        logger.info("File deleted", filename=filename)
    except Exception as e:
        logger.error("File deletion error", filename=filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )
