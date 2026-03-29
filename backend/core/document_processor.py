"""Document parsing and processing pipeline.

Supports: PDF, TXT, Markdown, DOCX — all using free libraries.
"""

import os
import uuid
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from core.chunking import chunk_text, ChunkData

LIGHTWEIGHT = os.environ.get("LIGHTWEIGHT_MODE", "false").lower() == "true"


def parse_document(file_path: str, file_type: str) -> str:
    """Extract raw text from a document file."""
    path = Path(file_path)

    if file_type == "pdf":
        return _parse_pdf(path)
    elif file_type == "docx":
        return _parse_docx(path)
    elif file_type in ("txt", "md"):
        return _parse_text(path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _parse_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(str(path))
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(pages)


def _parse_docx(path: Path) -> str:
    """Extract text from DOCX."""
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_text(path: Path) -> str:
    """Read plain text / markdown files."""
    import chardet
    raw = path.read_bytes()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    return raw.decode(encoding, errors="replace")


async def process_document(
    file_path: str,
    file_type: str,
    document_id: int,
    document_title: str,
    user_id: int,
) -> list[ChunkData]:
    """
    Full processing pipeline:
    1. Parse document → raw text
    2. Chunk text → smart segments
    3. Generate embeddings (local)
    4. Store in ChromaDB
    
    Returns the list of chunks created.
    """
    # Step 1: Parse
    raw_text = parse_document(file_path, file_type)
    if not raw_text.strip():
        raise ValueError("Document appears to be empty or could not be parsed.")

    # Step 2: Chunk
    chunks = chunk_text(raw_text, document_title)
    if not chunks:
        raise ValueError("No meaningful chunks could be extracted.")

    # Step 3: Generate chunk IDs and metadata
    chunk_texts = [c.text for c in chunks]
    chroma_ids = []
    metadatas = []
    for chunk in chunks:
        cid = f"doc{document_id}_chunk{chunk.index}_{uuid.uuid4().hex[:8]}"
        chroma_ids.append(cid)
        chunk.metadata["document_id"] = document_id
        chunk.metadata["chroma_id"] = cid
        metadatas.append(chunk.metadata)

    # Step 5: Store in indexes
    if LIGHTWEIGHT:
        from core.sparse_retriever import add_to_bm25
        add_to_bm25(user_id=user_id, ids=chroma_ids, texts=chunk_texts, metadatas=metadatas)
    else:
        from core.embeddings import generate_embeddings
        from core.vector_store import add_chunks
        from core.sparse_retriever import add_to_bm25

        # Dense index
        embeddings = generate_embeddings(chunk_texts)
        add_chunks(user_id=user_id, ids=chroma_ids, texts=chunk_texts, embeddings=embeddings, metadatas=metadatas)
        # Sparse index
        add_to_bm25(user_id=user_id, ids=chroma_ids, texts=chunk_texts, metadatas=metadatas)

    return chunks, chroma_ids