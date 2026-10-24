"""
Unit tests for core/extractor.py
"""

from pathlib import Path
import pytest
from core.extractor import (
    extract_file_content,
    format_file_size,
    ExtractedContent,
)
from core.demo_data import (
    create_sample_pdf,
    create_sample_docx,
    create_sample_png,
)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides a fresh temporary directory for file extraction tests."""
    work_dir = tmp_path / "test_extract"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert "KB" in format_file_size(2048)
    assert "MB" in format_file_size(1024 * 1024 * 5)


def test_extract_plain_text(temp_workspace: Path):
    txt_file = temp_workspace / "notes.txt"
    txt_file.write_text("CS 101 Lecture Notes on Sorting Algorithms", encoding="utf-8")

    result = extract_file_content(txt_file)
    assert result.is_supported is True
    assert result.is_image is False
    assert "Sorting Algorithms" in result.text_content
    assert result.file_name == "notes.txt"


def test_extract_empty_file(temp_workspace: Path):
    empty_file = temp_workspace / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    result = extract_file_content(empty_file)
    assert result.is_supported is True
    assert result.file_size_bytes == 0
    assert "[Empty File" in result.text_snippet


def test_extract_pdf(temp_workspace: Path):
    pdf_file = temp_workspace / "test_doc.pdf"
    create_sample_pdf(
        pdf_file,
        "Test Invoice Header",
        ["Total Amount: $500.00", "Payment Due immediately."]
    )

    result = extract_file_content(pdf_file)
    assert result.is_supported is True
    assert result.extension == ".pdf"
    assert "Test Invoice" in result.text_content
    assert "$500.00" in result.text_content


def test_extract_docx(temp_workspace: Path):
    docx_file = temp_workspace / "resume.docx"
    create_sample_docx(
        docx_file,
        "John Doe Resume",
        [("Experience", "Software Engineer at Tech Corp."), ("Education", "BS Computer Science")]
    )

    result = extract_file_content(docx_file)
    assert result.is_supported is True
    assert result.extension == ".docx"
    assert "John Doe" in result.text_content
    assert "Software Engineer" in result.text_content


def test_extract_image(temp_workspace: Path):
    png_file = temp_workspace / "diagram.png"
    create_sample_png(png_file, "System Architecture")

    result = extract_file_content(png_file)
    assert result.is_supported is True
    assert result.is_image is True
    assert result.image_metadata is not None
    assert result.image_metadata["width"] == 700
    assert result.image_metadata["height"] == 450


def test_extract_unsupported_file(temp_workspace: Path):
    bin_file = temp_workspace / "program.exe"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04")

    result = extract_file_content(bin_file)
    assert result.is_supported is False
    assert "not supported" in result.error_message
