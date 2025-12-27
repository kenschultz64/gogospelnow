import pytest
from fastapi.testclient import TestClient
import main
import time

@pytest.fixture
def client():
    app = main.create_app()
    return TestClient(app)

def test_get_listener_html(client):
    """Test that the listener HTML page is served correctly."""
    response = client.get("/listener")
    assert response.status_code == 200
    assert "<title>GoGospel Listener</title>" in response.text

def test_get_listener_status_initial(client):
    """Test initial state of the listener status endpoint."""
    response = client.get("/api/listener/status")
    assert response.status_code == 200
    data = response.json()
    assert "transcription" in data
    assert "translation" in data
    assert "audio_url" in data
    assert "timestamp" in data

def test_update_listener_data_reflection(client):
    """Test that updating data via main.py reflects in the API response."""
    test_trans = "Test Transcription"
    test_trans_text = "Test Translation"
    test_audio = "/audio/test.mp3"
    
    main.update_listener_data(transcription=test_trans, translation=test_trans_text, audio_url=test_audio)
    
    response = client.get("/api/listener/status")
    assert response.status_code == 200
    data = response.json()
    assert data["transcription"] == test_trans
    assert data["translation"] == test_trans_text
    assert data["audio_url"] == test_audio
    assert data["timestamp"] > 0

def test_static_audio_serving(client):
    """Test that files in temp_audio are served via /audio path."""
    import os
    if not os.path.exists("temp_audio"):
        os.makedirs("temp_audio")
    
    test_file = "temp_audio/test_serve.txt"
    with open(test_file, "w") as f:
        f.write("test audio data")
    
    response = client.get("/audio/test_serve.txt")
    assert response.status_code == 200
    assert response.text == "test audio data"
    
    os.remove(test_file)
