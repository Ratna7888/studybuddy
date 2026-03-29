"""Smart document chunking with metadata preservation."""

import re
from dataclasses import dataclass
from config import settings


@dataclass
class ChunkData:
    text: str
    index: int
    metadata: dict  # section, heading, page_num, etc.


def chunk_text(
    text: str,
    document_title: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> list[ChunkData]:
    """
    Chunk text using a paragraph-aware sliding window approach.
    Preserves section headings in metadata.
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # Clean the text
    text = _clean_text(text)
    if not text.strip():
        return []

    # Try section-based chunking first
    sections = _split_into_sections(text)

    chunks = []
    chunk_idx = 0

    for section_title, section_text in sections:
        # Split section into sized chunks
        section_chunks = _sliding_window_chunk(section_text, chunk_size, chunk_overlap)

        for chunk_text_piece in section_chunks:
            if len(chunk_text_piece.strip()) < 20:
                continue  # skip tiny fragments

            chunks.append(ChunkData(
                text=chunk_text_piece.strip(),
                index=chunk_idx,
                metadata={
                    "document_title": document_title,
                    "section": section_title or "Main Content",
                    "chunk_index": chunk_idx,
                },
            ))
            chunk_idx += 1

    return chunks


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and artifacts."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\t+', ' ', text)
    return text.strip()


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Split text by headings/sections.
    Detects markdown-style headings or all-caps lines.
    """
    # Pattern: markdown headings or lines that look like titles
    heading_pattern = re.compile(
        r'^(#{1,4}\s+.+|[A-Z][A-Z\s]{5,}[A-Z])$',
        re.MULTILINE
    )

    matches = list(heading_pattern.finditer(text))

    if not matches:
        return [("", text)]

    sections = []

    # Text before first heading
    if matches[0].start() > 0:
        pre = text[:matches[0].start()].strip()
        if pre:
            sections.append(("Introduction", pre))

    for i, match in enumerate(matches):
        title = match.group().strip().lstrip('#').strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))

    return sections if sections else [("", text)]


def _sliding_window_chunk(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, respecting sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        s_len = len(sentence.split())

        if current_len + s_len > size and current:
            chunks.append(' '.join(current))
            # Keep overlap
            overlap_sents = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s.split()) > overlap:
                    break
                overlap_sents.insert(0, s)
                overlap_len += len(s.split())
            current = overlap_sents
            current_len = overlap_len

        current.append(sentence)
        current_len += s_len

    if current:
        chunks.append(' '.join(current))

    return chunks