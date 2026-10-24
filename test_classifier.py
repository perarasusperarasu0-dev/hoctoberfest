"""
Unit tests for core/classifier.py
"""

from pathlib import Path
import pytest
from core.classifier import (
    SemanticClassifier,
    parse_ai_json_response,
    normalize_category,
    DEFAULT_CATEGORIES,
)
from core.extractor import ExtractedContent


def test_parse_ai_json_standard():
    raw = '{"category": "Finance", "reason": "Contains invoice billing information."}'
    cat, reason = parse_ai_json_response(raw)
    assert cat == "Finance"
    assert "invoice" in reason


def test_parse_ai_json_markdown_fenced():
    raw = """```json
{
  "category": "Work",
  "reason": "This is a resume describing professional software engineering experience."
}
```"""
    cat, reason = parse_ai_json_response(raw)
    assert cat == "Work"
    assert "resume" in reason


def test_parse_ai_json_imperfect_text():
    raw = 'Based on the review, "category": "Education", "reason": "Class lecture notes on math."'
    cat, reason = parse_ai_json_response(raw)
    assert cat == "Education"
    assert "lecture notes" in reason


def test_normalize_category():
    assert normalize_category("finance", DEFAULT_CATEGORIES) == "Finance"
    assert normalize_category("EDUCATION", DEFAULT_CATEGORIES) == "Education"
    assert normalize_category("UnknownAlienCategory", DEFAULT_CATEGORIES) == "Others"


def test_demo_classifier_finance():
    classifier = SemanticClassifier()
    dummy = ExtractedContent(
        file_path=Path("sample_invoice.pdf"),
        file_name="sample_invoice.pdf",
        extension=".pdf",
        file_size_bytes=1024,
        text_content="TAX INVOICE Total Due: $1,400.00 USD for cloud services.",
        text_snippet="TAX INVOICE Total Due...",
        is_image=False,
        is_supported=True,
    )
    res = classifier.classify_file(dummy, demo_mode=True)
    assert res.category == "Finance"
    assert res.is_demo is True


def test_demo_classifier_work():
    classifier = SemanticClassifier()
    dummy = ExtractedContent(
        file_path=Path("developer_resume.docx"),
        file_name="developer_resume.docx",
        extension=".docx",
        file_size_bytes=2048,
        text_content="John Doe - Work Experience: Senior Engineer, Technical Skills: Python, SQL.",
        text_snippet="John Doe - Work Experience...",
        is_image=False,
        is_supported=True,
    )
    res = classifier.classify_file(dummy, demo_mode=True)
    assert res.category == "Work"


def test_demo_classifier_education():
    classifier = SemanticClassifier()
    dummy = ExtractedContent(
        file_path=Path("lecture_slides.txt"),
        file_name="lecture_slides.txt",
        extension=".txt",
        file_size_bytes=512,
        text_content="CS 101 Lecture notes on binary trees and homework assignment.",
        text_snippet="CS 101 Lecture...",
        is_image=False,
        is_supported=True,
    )
    res = classifier.classify_file(dummy, demo_mode=True)
    assert res.category == "Education"


def test_ai_classifier_reports_image_limitation_with_text_model():
    """Verifies requirement: clearly report image-content analysis unavailable for text-only model."""
    classifier = SemanticClassifier()
    dummy_image = ExtractedContent(
        file_path=Path("photo.png"),
        file_name="photo.png",
        extension=".png",
        file_size_bytes=4096,
        text_content="",
        text_snippet="Image (PNG 500x500px)",
        is_image=True,
        is_supported=True,
    )

    # With text model 'llama3.2', it should report image-content analysis unavailable
    res = classifier.classify_file(dummy_image, model_name="llama3.2", demo_mode=False)
    assert res.category == "Images"
    assert "Image-content analysis is unavailable" in res.reason
    assert res.image_vision_used is False
