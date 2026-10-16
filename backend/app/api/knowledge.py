from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.db.user_models import User
from app.schemas.knowledge import KnowledgeCreateRequest, KnowledgeItem
from app.services.db_service import db_service
from app.services.file_parser_service import file_parser_service
from app.services.knowledge_service import knowledge_service
from app.services.storage_service import storage_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeItem])
async def list_knowledge(current_user: User = Depends(get_current_user)):
    return db_service.list_knowledge(current_user.id)


@router.get("/{document_id}", response_model=KnowledgeItem)
async def get_knowledge(document_id: str, current_user: User = Depends(get_current_user)):
    item = db_service.get_knowledge(current_user.id, document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    return item


@router.get("/{document_id}/download")
async def download_knowledge(document_id: str, current_user: User = Depends(get_current_user)):
    item = db_service.get_knowledge(current_user.id, document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    if not item.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This record has no file attachment")

    absolute_path = storage_service.resolve_path(item.file_path)
    if not absolute_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")

    return FileResponse(
        path=absolute_path,
        filename=item.file_name or item.title,
        media_type=item.mime_type or "application/octet-stream",
    )


@router.post("", response_model=KnowledgeItem)
async def create_knowledge(
    request: KnowledgeCreateRequest,
    current_user: User = Depends(get_current_user),
):
    item = db_service.create_knowledge(
        user_id=current_user.id,
        title=request.title,
        content=request.content,
        source=request.source,
        storage_provider="local",
        index_status="processing",
    )
    result = knowledge_service.index_document(current_user.id, item)
    status_text = "ready" if result.success else "keyword_only"
    updated = db_service.update_knowledge_status(
        current_user.id,
        item.id,
        chunk_count=result.chunk_count,
        index_status=status_text,
    )
    return updated or item


@router.post("/upload", response_model=KnowledgeItem)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    source: str = Form(default="upload"),
    title: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        parsed = file_parser_service.parse(
            file_name=file.filename or "document",
            mime_type=file.content_type,
            raw_bytes=raw_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    document_id = f"doc_{uuid4().hex[:12]}"
    stored = storage_service.save_file(
        user_id=current_user.id,
        document_id=document_id,
        file_name=file.filename or "document",
        content=raw_bytes,
    )

    item = db_service.create_knowledge(
        user_id=current_user.id,
        document_id=document_id,
        title=(title or stored.file_name.rsplit(".", 1)[0]).strip() or stored.file_name,
        content=parsed.content,
        source=source,
        file_name=stored.file_name,
        file_path=stored.relative_path,
        mime_type=parsed.mime_type,
        storage_provider="local",
        file_size=stored.size,
        index_status="processing",
    )

    result = knowledge_service.index_document(current_user.id, item)
    status_text = "ready" if result.success else "keyword_only"
    updated = db_service.update_knowledge_status(
        current_user.id,
        item.id,
        chunk_count=result.chunk_count,
        index_status=status_text,
    )
    return updated or item


@router.delete("/{document_id}")
async def delete_knowledge(document_id: str, current_user: User = Depends(get_current_user)):
    item = db_service.delete_knowledge(current_user.id, document_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    knowledge_service.delete_document(document_id)
    storage_service.delete_file(item.file_path)
    return {"success": True}
