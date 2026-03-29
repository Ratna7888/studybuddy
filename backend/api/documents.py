"""Document upload, listing, and management routes."""

import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models import User, Document, Chunk
from api.auth import get_current_user
from core.document_processor import process_document
from core.vector_store import delete_document_chunks
from core.sparse_retriever import remove_document_from_bm25
from config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a document and trigger background processing."""
    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {settings.allowed_extensions}")

    # Save file to disk
    user_dir = Path(settings.upload_dir) / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create document record
    doc = Document(
        user_id=user.id,
        title=file.filename.rsplit(".", 1)[0],
        file_path=str(file_path),
        file_type=ext,
        processing_status="processing",
    )
    db.add(doc)
    await db.flush()
    doc_id = doc.id

    # Process in background
    background_tasks.add_task(
        _process_document_task, doc_id, str(file_path), ext, file.filename, user.id
    )

    return {
        "id": doc_id,
        "title": doc.title,
        "status": "processing",
        "message": "Document uploaded and processing started.",
    }


async def _process_document_task(
    doc_id: int, file_path: str, file_type: str, title: str, user_id: int
):
    """Background task: parse, chunk, embed, store."""
    from db.database import async_session

    async with async_session() as db:
        try:
            chunks, chroma_ids = await process_document(
                file_path=file_path,
                file_type=file_type,
                document_id=doc_id,
                document_title=title,
                user_id=user_id,
            )

            # Save chunk records to SQLite
            for chunk_data, cid in zip(chunks, chroma_ids):
                chunk = Chunk(
                    document_id=doc_id,
                    chunk_text=chunk_data.text,
                    chunk_index=chunk_data.index,
                    metadata_json=chunk_data.metadata,
                    chroma_id=cid,
                )
                db.add(chunk)

            # Update document status
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one()
            doc.processing_status = "ready"
            doc.chunk_count = len(chunks)
            await db.commit()

            print(f"Document '{title}' processed: {len(chunks)} chunks created.")

        except Exception as e:
            # Mark as failed
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.processing_status = "failed"
                await db.commit()
            print(f"Error processing document: {e}")


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all documents for the current user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "file_type": d.file_type,
            "processing_status": d.processing_status,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get document detail with chunk previews."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Get chunks
    chunk_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
    )
    chunks = chunk_result.scalars().all()

    return {
        "id": doc.id,
        "title": doc.title,
        "file_type": doc.file_type,
        "processing_status": doc.processing_status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text_preview": c.chunk_text[:200],
                "metadata": c.metadata_json,
            }
            for c in chunks
        ],
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a document and its chunks."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Remove from vector store
    delete_document_chunks(user.id, doc_id)

    # Remove from BM25 index
    remove_document_from_bm25(user.id, doc_id)

    # Remove file
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    # Remove from DB (cascades to chunks)
    await db.delete(doc)

    return {"message": "Document deleted successfully."}