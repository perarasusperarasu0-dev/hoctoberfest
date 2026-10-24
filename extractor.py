"""
LazySort - Document and Metadata Extractor
Handles reading and text extraction from PDF, DOCX, TXT, and Images safely.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class ExtractedContent:
    file_path: Path
    file_name: str
    extension: str
    file_size_bytes: int
    text_content: str
    text_snippet: str
    is_image: bool
    is_supported: bool
    error_message: Optional[str] = None
    image_metadata: Optional[dict] = None


SUPPORTED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".log", ".py", ".html", ".xml", ".yaml", ".yml"
}
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"
}
SUPPORTED_DOC_EXTENSIONS = {
    ".pdf", ".docx"
}
ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS
)


def format_file_size(size_bytes: int) -> str:
    """Returns a beginner-friendly human readable file size string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def extract_from_plain_text(file_path: Path, max_chars: int = 4000) -> str:
    """Reads plain text files safely using UTF-8 with latin-1 fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                return f.read(max_chars).strip()
        except Exception:
            continue
    return ""


def extract_from_pdf(file_path: Path, max_pages: int = 5, max_chars: int = 4000) -> str:
    """Extracts text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        if reader.is_encrypted:
            return "[Encrypted PDF - Password Protected]"

        extracted = []
        for i, page in enumerate(reader.pages[:max_pages]):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted.append(page_text.strip())

        full_text = "\n\n".join(extracted)
        return full_text[:max_chars].strip()
    except Exception as e:
        raise RuntimeError(f"Could not read PDF: {str(e)}")


def extract_from_docx(file_path: Path, max_chars: int = 4000) -> str:
    """Extracts text from paragraphs and tables in a Word document (.docx)."""
    try:
        from docx import Document
        doc = Document(str(file_path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Also inspect table cells for invoices, forms, etc.
        table_texts = []
        for table in doc.tables[:3]:  # First 3 tables
            for row in table.rows:
                row_str = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_str:
                    table_texts.append(row_str)

        combined = "\n".join(paragraphs + table_texts)
        return combined[:max_chars].strip()
    except Exception as e:
        raise RuntimeError(f"Could not read Word document: {str(e)}")


def extract_from_image(file_path: Path) -> dict:
    """Extracts image metadata safely using Pillow."""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            return {
                "format": img.format or file_path.suffix.upper().replace(".", ""),
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
            }
    except Exception as e:
        raise RuntimeError(f"Could not inspect image: {str(e)}")


def extract_file_content(file_path: Path, max_chars: int = 3000) -> ExtractedContent:
    """
    Main extraction entry point.
    Safely inspects the file, extracts textual representation or image metadata,
    and returns a normalized ExtractedContent object.
    """
    path = Path(file_path)
    if not path.is_file():
        return ExtractedContent(
            file_path=path,
            file_name=path.name,
            extension=path.suffix.lower(),
            file_size_bytes=0,
            text_content="",
            text_snippet="",
            is_image=False,
            is_supported=False,
            error_message="File does not exist or is not a regular file."
        )

    ext = path.suffix.lower()
    file_size = path.stat().st_size

    # Check for empty files
    if file_size == 0:
        return ExtractedContent(
            file_path=path,
            file_name=path.name,
            extension=ext,
            file_size_bytes=0,
            text_content="",
            text_snippet="[Empty File - 0 Bytes]",
            is_image=False,
            is_supported=True,
            error_message=None
        )

    # 1. Plain text and code files
    if ext in SUPPORTED_TEXT_EXTENSIONS:
        try:
            content = extract_from_plain_text(path, max_chars=max_chars)
            snippet = (content[:250] + "...") if len(content) > 250 else content
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content=content,
                text_snippet=snippet or "[Empty text content]",
                is_image=False,
                is_supported=True,
            )
        except Exception as e:
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content="",
                text_snippet="",
                is_image=False,
                is_supported=False,
                error_message=str(e),
            )

    # 2. PDF Documents
    if ext == ".pdf":
        try:
            content = extract_from_pdf(path, max_chars=max_chars)
            snippet = (content[:250] + "...") if len(content) > 250 else content
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content=content,
                text_snippet=snippet or "[PDF with no extractable text / Scanned page]",
                is_image=False,
                is_supported=True,
            )
        except Exception as e:
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content="",
                text_snippet="",
                is_image=False,
                is_supported=False,
                error_message=str(e),
            )

    # 3. Word Documents (.docx)
    if ext == ".docx":
        try:
            content = extract_from_docx(path, max_chars=max_chars)
            snippet = (content[:250] + "...") if len(content) > 250 else content
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content=content,
                text_snippet=snippet or "[DOCX with no extractable text]",
                is_image=False,
                is_supported=True,
            )
        except Exception as e:
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content="",
                text_snippet="",
                is_image=False,
                is_supported=False,
                error_message=str(e),
            )

    # 4. Image Files
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        try:
            meta = extract_from_image(path)
            snippet = f"Image ({meta['format']} {meta['width']}x{meta['height']}px, mode: {meta['mode']})"
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content="",
                text_snippet=snippet,
                is_image=True,
                is_supported=True,
                image_metadata=meta,
            )
        except Exception as e:
            return ExtractedContent(
                file_path=path,
                file_name=path.name,
                extension=ext,
                file_size_bytes=file_size,
                text_content="",
                text_snippet="",
                is_image=True,
                is_supported=False,
                error_message=str(e),
            )

    # 5. Unsupported file types
    return ExtractedContent(
        file_path=path,
        file_name=path.name,
        extension=ext,
        file_size_bytes=file_size,
        text_content="",
        text_snippet=f"Unsupported format '{ext or 'unknown'}'",
        is_image=False,
        is_supported=False,
        error_message=f"File extension '{ext}' is not supported for content extraction."
    )
