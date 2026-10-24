"""
Unit tests for core/ollama_client.py
"""

from core.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)


def test_vision_capable_detection():
    client = OllamaClient()
    assert client.is_vision_capable("llava") is True
    assert client.is_vision_capable("llava:13b") is True
    assert client.is_vision_capable("llama3.2-vision") is True
    assert client.is_vision_capable("llama3.2") is False
    assert client.is_vision_capable("mistral:latest") is False
    assert client.is_vision_capable("phi3") is False


def test_check_health_offline_handling():
    # Test against an invalid port
    client = OllamaClient(base_url="http://127.0.0.1:59999")
    health = client.check_health()
    assert health["ok"] is False
    assert health["version"] is None
    assert health["error"] is not None


def test_ollama_connection_error_instructions():
    err = OllamaConnectionError("http://localhost:11434")
    msg = str(err)
    assert "https://ollama.com/download" in msg
    assert "ollama serve" in msg
    assert "Safe Demo Mode" in msg


def test_ollama_model_not_found_error_instructions():
    err = OllamaModelNotFoundError("deepseek-r1", ["llama3.2", "phi3"])
    msg = str(err)
    assert "ollama pull deepseek-r1" in msg
    assert "llama3.2" in msg
