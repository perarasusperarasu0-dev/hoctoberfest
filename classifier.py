"""
LazySort - Semantic File Classifier
Connects extracted content to actual Ollama AI models for classification,
handles image vision analysis or reports text-only model limits,
and includes a transparent demo classification engine.
"""

from dataclasses import dataclass
import json
import re
from typing import List, Optional, Tuple
from pathlib import Path

from core.extractor import ExtractedContent
from core.ollama_client import OllamaClient, OllamaError


DEFAULT_CATEGORIES = [
    "Documents",
    "Education",
    "Work",
    "Finance",
    "Images",
    "Others",
]

CATEGORY_DESCRIPTIONS = {
    "Documents": "General personal or official papers, legal agreements, identification, letters, certificates, and forms.",
    "Education": "Academic lecture notes, study materials, homework, research papers, textbooks, and course syllabus.",
    "Work": "Resumes/CVs, job applications, project specifications, meeting minutes, client contracts, and work memos.",
    "Finance": "Invoices, payment receipts, bank statements, tax records, expense budgets, and bills.",
    "Images": "Photographs, digital artwork, screenshots, icons, diagrams, and graphic visual media.",
    "Others": "Unclassified items, installation files, archives, code scripts, or files with unreadable contents.",
}


@dataclass
class ClassificationResult:
    file_path: Path
    file_name: str
    category: str
    reason: str
    is_demo: bool
    is_image: bool
    image_vision_used: bool = False
    warning: Optional[str] = None


def normalize_category(raw_category: str, allowed_categories: List[str]) -> str:
    """Matches raw model category output to an allowed category case-insensitively."""
    cleaned = raw_category.strip().title()
    for cat in allowed_categories:
        if cleaned.lower() == cat.lower():
            return cat
    # Partial matching check
    for cat in allowed_categories:
        if cat.lower() in cleaned.lower():
            return cat
    return "Others"


def parse_ai_json_response(raw_text: str) -> Tuple[str, str]:
    """Extracts category and reason from Ollama model's text response."""
    # Strip markdown code blocks if present
    cleaned = raw_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    # Try standard json parse
    try:
        data = json.loads(cleaned)
        category = str(data.get("category", "")).strip()
        reason = str(data.get("reason", "")).strip()
        if category:
            return category, reason or "Classified based on semantic document content."
    except Exception:
        pass

    # Regex fallback if JSON was slightly malformed by small models
    cat_match = re.search(r'"category"\s*:\s*"([^"]+)"', raw_text, re.IGNORECASE)
    reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', raw_text, re.IGNORECASE)

    if cat_match:
        cat = cat_match.group(1).strip()
        reason = reason_match.group(1).strip() if reason_match else "Extracted from AI response."
        return cat, reason

    # Plain text search for category keyword
    for cat in DEFAULT_CATEGORIES:
        if re.search(rf"\b{cat}\b", raw_text, re.IGNORECASE):
            return cat, f"AI identified category '{cat}' in its analysis."

    return "Others", "Could not unambiguously parse AI response; placed into Others."


class SemanticClassifier:
    """Classifies files using real Ollama AI or safe demo heuristics."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        categories: Optional[List[str]] = None,
    ):
        self.ollama = ollama_client or OllamaClient()
        self.categories = categories or DEFAULT_CATEGORIES

    def classify_file(
        self,
        extracted: ExtractedContent,
        model_name: str = "llama3.2",
        demo_mode: bool = False,
    ) -> ClassificationResult:
        """
        Classifies a single extracted file.
        In AI mode: executes an actual prompt against Ollama.
        In Demo mode: applies safe transparent rule-based classification.
        """
        if demo_mode:
            return self._classify_demo(extracted)

        return self._classify_ai(extracted, model_name)

    def _classify_ai(
        self, extracted: ExtractedContent, model_name: str
    ) -> ClassificationResult:
        """Performs actual AI classification via Ollama."""

        # 1. Handle Images
        if extracted.is_image:
            # Check if model has vision capabilities
            is_vision = self.ollama.is_vision_capable(model_name)
            if not is_vision:
                # Clearly report that image-content analysis is unavailable with text model
                return ClassificationResult(
                    file_path=extracted.file_path,
                    file_name=extracted.file_name,
                    category="Images",
                    reason=(
                        f"Image-content analysis is unavailable with text-only model '{model_name}'. "
                        "Categorized into 'Images' by file format. "
                        "To inspect visual contents (e.g. photos of receipts vs artwork), install a vision model like 'llava'."
                    ),
                    is_demo=False,
                    is_image=True,
                    image_vision_used=False,
                    warning="Text-only model: visual content not inspected.",
                )

            # Vision model is available: encode and send
            try:
                base64_img = self.ollama.encode_image_base64(extracted.file_path)
                prompt = (
                    "Look at this image. Classify it into exactly one of these categories: "
                    f"{', '.join(self.categories)}.\n\n"
                    "Rules:\n"
                    "- If it is a photo or scan of a receipt, bill, or invoice: classify as Finance.\n"
                    "- If it is a slide, diagram, study note, or textbook page: classify as Education.\n"
                    "- If it is a resume, contract, or workplace document: classify as Work.\n"
                    "- If it is an ID, legal certificate, or official form: classify as Documents.\n"
                    "- If it is a standard photo, graphic, wallpaper, or icon: classify as Images.\n"
                    "- Otherwise: classify as Others.\n\n"
                    "Respond ONLY with valid JSON in this exact format:\n"
                    '{"category": "CategoryName", "reason": "Short explanation of what you see in the image"}'
                )

                raw_response = self.ollama.generate(
                    model=model_name,
                    prompt=prompt,
                    images=[base64_img],
                    format_json=True,
                )
                raw_cat, reason = parse_ai_json_response(raw_response)
                category = normalize_category(raw_cat, self.categories)
                return ClassificationResult(
                    file_path=extracted.file_path,
                    file_name=extracted.file_name,
                    category=category,
                    reason=f"[Vision AI] {reason}",
                    is_demo=False,
                    is_image=True,
                    image_vision_used=True,
                )
            except OllamaError as e:
                # If vision fails, provide clear error reason
                return ClassificationResult(
                    file_path=extracted.file_path,
                    file_name=extracted.file_name,
                    category="Images",
                    reason=f"Vision model error: {str(e)}. Defaulted to Images.",
                    is_demo=False,
                    is_image=True,
                    image_vision_used=False,
                    warning=str(e),
                )

        # 2. Handle Text Documents (PDF, DOCX, TXT)
        text = extracted.text_content.strip()
        if not text:
            # If no text was extracted (e.g. empty or unsupported)
            if not extracted.is_supported:
                return ClassificationResult(
                    file_path=extracted.file_path,
                    file_name=extracted.file_name,
                    category="Others",
                    reason=extracted.error_message or "Unsupported file format.",
                    is_demo=False,
                    is_image=False,
                    warning="No text content could be extracted.",
                )
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Others",
                reason="File is empty or contains no extractable text.",
                is_demo=False,
                is_image=False,
            )

        # Build prompt for text classification
        cat_definitions = "\n".join(
            f"- {cat}: {CATEGORY_DESCRIPTIONS.get(cat, '')}" for cat in self.categories
        )

        prompt = (
            "You are an expert file organizer. Classify the following document into EXACTLY ONE "
            f"of these categories:\n{cat_definitions}\n\n"
            f"File Name: {extracted.file_name}\n"
            f"File Size: {extracted.file_size_bytes} bytes\n\n"
            "Document Text Preview:\n"
            "--- BEGIN CONTENT ---\n"
            f"{text[:2000]}\n"
            "--- END CONTENT ---\n\n"
            "Analyze the content and respond ONLY with a JSON object in this format:\n"
            '{"category": "CategoryName", "reason": "Concise 1-sentence reason referencing specific details found in the content"}'
        )

        raw_response = self.ollama.generate(
            model=model_name,
            prompt=prompt,
            format_json=True,
        )

        raw_cat, reason = parse_ai_json_response(raw_response)
        category = normalize_category(raw_cat, self.categories)

        return ClassificationResult(
            file_path=extracted.file_path,
            file_name=extracted.file_name,
            category=category,
            reason=f"[Ollama {model_name}] {reason}",
            is_demo=False,
            is_image=False,
            image_vision_used=False,
        )

    def _classify_demo(self, extracted: ExtractedContent) -> ClassificationResult:
        """
        Transparent rule-based heuristic for Safe Demo Mode.
        Enables testing UI and file organization flows before Ollama is installed.
        """
        text_lower = (extracted.text_content + " " + extracted.file_name).lower()

        if extracted.is_image:
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Images",
                reason="[DEMO MODE] Image format recognized (.png/.jpg).",
                is_demo=True,
                is_image=True,
                image_vision_used=False,
            )

        def matches_any(keywords):
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                    return True
            return False

        # Finance indicators
        finance_keywords = [
            "invoice", "receipt", "payment", "subtotal", "tax", "total due",
            "bank statement", "billing", "usd", "eur", "amount due", "salary"
        ]
        if matches_any(finance_keywords):
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Finance",
                reason="[DEMO MODE] Content contains financial transaction and billing terms.",
                is_demo=True,
                is_image=False,
            )

        # Work indicators
        work_keywords = [
            "resume", "curriculum vitae", "work experience", "technical skills", "job",
            "meeting minutes", "project roadmap", "deliverables", "nda", "employment"
        ]
        if matches_any(work_keywords):
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Work",
                reason="[DEMO MODE] Content contains career or professional work indicators.",
                is_demo=True,
                is_image=False,
            )

        # Education indicators
        edu_keywords = [
            "lecture", "homework", "syllabus", "exam", "course", "study guide",
            "university", "professor", "chapter", "assignment", "grade", "quiz"
        ]
        if matches_any(edu_keywords):
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Education",
                reason="[DEMO MODE] Content references coursework, lectures, or study materials.",
                is_demo=True,
                is_image=False,
            )

        # Documents indicators
        doc_keywords = [
            "certificate", "agreement", "passport", "license", "official",
            "affidavit", "registration", "notice", "contract", "lease"
        ]
        if matches_any(doc_keywords):
            return ClassificationResult(
                file_path=extracted.file_path,
                file_name=extracted.file_name,
                category="Documents",
                reason="[DEMO MODE] Content matches official document or certificate patterns.",
                is_demo=True,
                is_image=False,
            )

        # Default fallback
        return ClassificationResult(
            file_path=extracted.file_path,
            file_name=extracted.file_name,
            category="Others",
            reason="[DEMO MODE] General content placed in Others.",
            is_demo=True,
            is_image=False,
        )
