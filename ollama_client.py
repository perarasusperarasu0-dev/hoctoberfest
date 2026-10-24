"""
LazySort - Ollama Client & Health Diagnostics
Interacts with the local Ollama REST API.
Handles actual open-weight models, image vision encoding, and beginner-friendly error messages.
"""

import base64
from pathlib import Path
from typing import List, Optional, Dict, Any
import requests


DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TEXT_MODEL = "qwen2.5:0.5b"

KNOWN_VISION_MODELS = {
    "llava", "llama3.2-vision", "bakllava", "moondream", "minicpm-v", "qwen2-vl", "qwen-vl"
}


class OllamaError(Exception):
    """Base exception for Ollama interactions."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when the Ollama server cannot be reached."""
    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL):
        message = (
            f"Could not connect to Ollama at '{base_url}'.\n\n"
            "Possible causes:\n"
            " 1. Ollama is not installed.\n"
            "    -> Download for Windows at: https://ollama.com/download\n"
            " 2. Ollama is installed but not running.\n"
            "    -> Open PowerShell and run: ollama serve\n"
            "    -> Or start the Ollama desktop app from your Windows Start menu.\n"
            " 3. You can also turn on 'Safe Demo Mode' to test LazySort right now!"
        )
        super().__init__(message)
        self.base_url = base_url


class OllamaModelNotFoundError(OllamaError):
    """Raised when the specified model is not downloaded in Ollama."""
    def __init__(self, model_name: str, available_models: List[str]):
        avail_str = ", ".join(available_models) if available_models else "None"
        message = (
            f"Ollama model '{model_name}' was not found on your machine.\n\n"
            f"Currently installed models: {avail_str}\n\n"
            f"To install this model, open Windows PowerShell and run:\n"
            f"   ollama pull {model_name}\n\n"
            f"Recommended lightweight models:\n"
            f"   ollama pull llama3.2       (Small & fast - 2GB)\n"
            f"   ollama pull phi3           (Lightweight - 2.2GB)\n"
            f"   ollama pull llava          (For document & image vision - 4.7GB)"
        )
        super().__init__(message)
        self.model_name = model_name
        self.available_models = available_models


class OllamaClient:
    """Client for querying the local Ollama instance."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, timeout: int = 45):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """
        Pings Ollama to verify if the service is running.
        Returns a dict with 'ok': bool, 'version': str or None, and 'error': str or None.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/version", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                return {"ok": True, "version": data.get("version", "unknown"), "error": None}
            return {
                "ok": False,
                "version": None,
                "error": f"Ollama returned unexpected status code {resp.status_code}",
            }
        except requests.exceptions.RequestException as e:
            return {"ok": False, "version": None, "error": str(e)}
            
    def list_models(self) -> List[str]:
        """
        Fetches the list of installed model names from Ollama.
        Raises OllamaConnectionError if Ollama is unreachable.
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                raise OllamaError(f"Failed to fetch models: HTTP {resp.status_code}")
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            return models
        except requests.exceptions.RequestException:
            raise OllamaConnectionError(self.base_url)

    def is_vision_capable(self, model_name: str) -> bool:
        """Determines if the given model likely supports visual inputs."""
        clean = model_name.lower().split(":")[0]
        return any(v in clean for v in KNOWN_VISION_MODELS)

    def encode_image_base64(self, image_path: Path) -> str:
        """Encodes an image file into base64 string for Ollama vision API."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[str]] = None,
        format_json: bool = False,
    ) -> str:
        """
        Sends an actual classification prompt to Ollama.
        Does not mock or fake responses.
        """
        health = self.check_health()
        if not health["ok"]:
            raise OllamaConnectionError(self.base_url)

        # Verify model exists
        installed = self.list_models()
        # Allow matching with or without tag e.g. "llama3.2" matches "llama3.2:latest"
        model_found = any(
            m == model or m.startswith(f"{model}:") or model.startswith(f"{m}:")
            for m in installed
        )
        if not model_found and installed:
            raise OllamaModelNotFoundError(model, installed)

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic classification
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        if images:
            payload["images"] = images

        if format_json:
            payload["format"] = "json"

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                raise OllamaError(
                    f"Ollama API error (HTTP {resp.status_code}): {resp.text}"
                )
            result = resp.json()
            return result.get("response", "").strip()
        except requests.exceptions.Timeout:
            raise OllamaError(
                f"Model '{model}' timed out after {self.timeout}s. "
                "Try a smaller model like 'llama3.2:1b' or 'phi3'."
            )
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"Communication error with Ollama: {str(e)}")
