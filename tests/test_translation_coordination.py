import pytest
from unittest.mock import patch, MagicMock
from translator_core import get_translation_client, translate

def test_get_translation_client_ollama():
    """Test Ollama client initialization."""
    settings = {
        "translation_provider": "Ollama",
        "translation_server": "http://test-server:11434"
    }
    with patch("translator_core.OpenAI") as mock_openai:
        client, model, error = get_translation_client(settings)
        assert error is None
        mock_openai.assert_called_once_with(base_url="http://test-server:11434/v1", api_key="ollama")

def test_get_translation_client_openai():
    """Test OpenAI client initialization."""
    settings = {
        "translation_provider": "OpenAI",
        "openai_api_key": "test-key"
    }
    with patch("translator_core.OpenAI") as mock_openai:
        client, model, error = get_translation_client(settings)
        assert error is None
        mock_openai.assert_called_once_with(base_url="https://api.openai.com/v1", api_key="test-key")

def test_get_translation_client_missing_key():
    """Test error handling when API key is missing."""
    settings = {
        "translation_provider": "OpenAI",
        "openai_api_key": ""
    }
    client, model, error = get_translation_client(settings)
    assert "API Key required for OpenAI" in error

def test_translate_success():
    """Test successful translation coordination."""
    settings = {
        "translation_provider": "Ollama",
        "translation_server": "http://localhost:11434"
    }
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hola"
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch("translator_core.get_translation_client", return_value=(mock_client, None, None)):
        with patch("translator_core.log_translation_file"):
            result = translate("Hello", "English", "Spanish", "test-model", settings)
            assert result == "Hola"
            mock_client.chat.completions.create.assert_called_once()
