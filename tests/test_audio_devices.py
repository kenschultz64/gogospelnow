import pytest
from unittest.mock import patch, MagicMock
import main
import sys

def test_get_audio_devices_basic():
    """Test basic device discovery with mocked sounddevice."""
    mock_devices = [
        {'name': 'Mic 1', 'max_input_channels': 1, 'max_output_channels': 0, 'hostapi': 0},
        {'name': 'Speaker 1', 'max_input_channels': 0, 'max_output_channels': 2, 'hostapi': 0}
    ]
    
    with patch('sounddevice.query_devices', return_value=mock_devices):
        with patch('sounddevice.default.device', [0, 1]):
            # Use side_effect to return the mock_hostapi for any index
            with patch('sounddevice.query_hostapis', return_value=[{'name': 'MME'}]):
                inputs, outputs, def_in, def_out = main.get_audio_devices()
                
                # Check inputs (1 real + 1 virtual fallback)
                assert len(inputs) == 2
                assert "Mic 1" in inputs[0][0]
                assert inputs[1][0] == "Virtual Microphone (Fallback)"
                
                # Check outputs (1 real + 1 virtual fallback)
                assert len(outputs) == 2
                assert "Speaker 1" in outputs[0][0]
                assert outputs[1][0] == "Virtual Speaker (Fallback)"
                
                # Check default indices
                assert def_in == 0
                assert def_out == 1

def test_get_audio_devices_prioritization():
    """Test that Windows specific devices are prioritized if on Windows."""
    mock_devices = [
        {'name': 'Standard Mic', 'max_input_channels': 1, 'max_output_channels': 0, 'hostapi': 0},
        {'name': 'Microphone (High Definition Audio Device)', 'max_input_channels': 1, 'max_output_channels': 0, 'hostapi': 0}
    ]
    
    with patch('sounddevice.query_devices', return_value=mock_devices):
        with patch('sounddevice.default.device', [0, 0]):
            with patch('sounddevice.query_hostapis', return_value=[{'name': 'MME'}]):
                with patch('sys.platform', 'win32'):
                    inputs, outputs, def_in, def_out = main.get_audio_devices()
                    
                    # The High Definition Audio Device should be first due to Windows prioritization
                    assert "High Definition Audio Device" in inputs[0][0]
                    assert "Standard Mic" in inputs[1][0]
