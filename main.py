# SPDX-License-Identifier: Apache-2.0

import os
import numpy as np
import sounddevice as sd
import queue
import threading
import asyncio
import time
import json
import glob
import gradio as gr
from faster_whisper import WhisperModel
from scipy.signal import resample

# Import core functionality
import translator_core as core

# --- Global Variables & Queues ---
audio_queue = queue.Queue()
stop_event = threading.Event()
recording_thread = None
whisper_model = None
current_settings = core.load_settings()

# CPU optimization: Set thread limits
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

# --- Cleanup old temp files ---
def cleanup_temp_files():
    temp_files = glob.glob("temp_tts_output_*.mp3")
    for f in temp_files:
        try:
            os.remove(f)
            core.log_message(f"Removed old temp file: {f}", "INFO")
        except OSError as e:
            core.log_message(f"Error removing file {f}: {e}", "ERROR")

cleanup_temp_files()

# --- Runtime timing params (tunable via Settings UI) ---
# CPU-optimized defaults for better performance
RUNTIME_PARAMS = {
    "block_duration_ms": 50,   # Increased from 20ms for CPU efficiency
    "min_silence_s": 0.8,     # Increased from 0.6s to reduce processing frequency
    "min_speech_s": 1.5,      # Increased from 1.0s for better batching
    "max_speech_s": 8.0,      # Reduced from 10.0s to limit buffer size
    "overlap_s": 0.5          # keep tail after processing to not lose boundary words
}

# Quick preset definitions for timing and VAD
PRESETS = {
    "Balanced": {
        "block_ms": 22,
        "overlap_ms": 550,
        "min_silence_ms": 650,
        "min_speech_ms": 1100,
        "max_speech_s": 11,
        "no_speech": 0.7,
        "vad": False,
    },
    "Lowest Latency": {
        "block_ms": 20,
        "overlap_ms": 450,
        "min_silence_ms": 550,
        "min_speech_ms": 950,
        "max_speech_s": 9,
        "no_speech": 0.67,
        "vad": False,
    },
    "Maximum Readability": {
        "block_ms": 28,
        "overlap_ms": 650,
        "min_silence_ms": 750,
        "min_speech_ms": 1300,
        "max_speech_s": 13,
        "no_speech": 0.78,
        "vad": False,
    },
}
available_ollama_models = core.fetch_ollama_models()
input_devices = []
output_devices = []
selected_output_device_name = None

# --- User Preferences ---
USER_PREFERENCES_FILE = "user_preferences.json"

def load_user_preferences():
    """Load user preferences from file or return defaults."""
    try:
        if os.path.exists(USER_PREFERENCES_FILE):
            with open(USER_PREFERENCES_FILE, "r") as f:
                prefs = json.load(f)
                core.log_message(f"Loaded user preferences from {USER_PREFERENCES_FILE}")
                return prefs
        else:
            core.log_message(f"{USER_PREFERENCES_FILE} not found. Using defaults.")
    except Exception as e:
        core.log_message(f"Error loading user preferences: {e}", "ERROR")
    
    # Default preferences
    return {
        "source_language": "Auto-Detect",
        "target_language": "🇺🇸 American English",
        "ollama_model": "",
        "voice": "em_alex"
    }

def save_user_preferences(prefs):
    """Save user preferences to file."""
    try:
        # Ensure everything is JSON-serializable (no numpy types, etc.)
        def sanitize_for_json(obj):
            import numpy as _np
            if isinstance(obj, (str, bool)) or obj is None:
                return obj
            if isinstance(obj, (int, float)):
                return obj
            if isinstance(obj, _np.generic):
                # Convert numpy scalar to Python scalar
                return obj.item()
            if isinstance(obj, (list, tuple)):
                return [sanitize_for_json(x) for x in obj]
            if isinstance(obj, dict):
                return {str(k): sanitize_for_json(v) for k, v in obj.items()}
            # Fallback to string for unknown types
            try:
                return json.loads(json.dumps(obj))
            except Exception:
                return str(obj)

        sanitized = sanitize_for_json(prefs)
        with open(USER_PREFERENCES_FILE, "w") as f:
            json.dump(sanitized, f, indent=2)
        core.log_message(f"Saved user preferences to {USER_PREFERENCES_FILE}")
        return True
    except Exception as e:
        core.log_message(f"Error saving user preferences: {e}", "ERROR")
        return False

# Load user preferences
user_preferences = load_user_preferences()

# --- Circular Audio Buffer Class for CPU Optimization ---
class CircularAudioBuffer:
    """Efficient circular buffer to avoid numpy concatenation overhead."""
    def __init__(self, max_duration_seconds=30):
        self.max_size = int(core.TARGET_RATE * max_duration_seconds)
        self.buffer = np.zeros(self.max_size, dtype=np.float32)
        self.write_pos = 0
        self.data_size = 0
        
    def add_audio(self, audio_chunk):
        """Add audio chunk to buffer efficiently."""
        chunk_size = len(audio_chunk)
        
        if chunk_size >= self.max_size:
            # If chunk is larger than buffer, just keep the end
            self.buffer[:] = audio_chunk[-self.max_size:]
            self.write_pos = 0
            self.data_size = self.max_size
            return
            
        # Check if we need to wrap around
        if self.write_pos + chunk_size <= self.max_size:
            self.buffer[self.write_pos:self.write_pos + chunk_size] = audio_chunk
            self.write_pos += chunk_size
        else:
            # Wrap around
            first_part = self.max_size - self.write_pos
            self.buffer[self.write_pos:] = audio_chunk[:first_part]
            self.buffer[:chunk_size - first_part] = audio_chunk[first_part:]
            self.write_pos = chunk_size - first_part
            
        self.data_size = min(self.data_size + chunk_size, self.max_size)
    
    def get_audio(self, duration_seconds=None):
        """Get audio from buffer as contiguous array."""
        if duration_seconds is None:
            samples_needed = self.data_size
        else:
            samples_needed = min(int(core.TARGET_RATE * duration_seconds), self.data_size)
            
        if samples_needed == 0:
            return np.array([], dtype=np.float32)
            
        if samples_needed <= self.data_size and self.write_pos >= samples_needed:
            # Simple case: data is contiguous before write_pos
            return self.buffer[self.write_pos - samples_needed:self.write_pos].copy()
        else:
            # Need to handle wrap-around
            result = np.zeros(samples_needed, dtype=np.float32)
            if self.data_size < self.max_size:
                # Buffer not full yet
                result[:] = self.buffer[:samples_needed]
            else:
                # Buffer is full, need to reconstruct order
                if self.write_pos == 0:
                    result[:] = self.buffer[-samples_needed:]
                else:
                    first_part = min(samples_needed, self.max_size - self.write_pos)
                    result[:first_part] = self.buffer[self.write_pos:self.write_pos + first_part]
                    if samples_needed > first_part:
                        remaining = samples_needed - first_part
                        result[first_part:] = self.buffer[:remaining]
            return result
    
    def clear(self):
        """Clear the buffer."""
        self.write_pos = 0
        self.data_size = 0
        
    def get_overlap(self, overlap_seconds):
        """Get overlap audio for continuity."""
        overlap_samples = int(core.TARGET_RATE * overlap_seconds)
        return self.get_audio(overlap_seconds) if overlap_samples <= self.data_size else np.array([], dtype=np.float32)

# --- Whisper Model Singleton ---
def get_whisper_model():
    """Get or create the global Whisper model instance with hardware detection."""
    global whisper_model
    if whisper_model is None:
        # Get hardware preferences
        device_pref = user_preferences.get("compute_device", "CPU Only")
        compute_type = user_preferences.get("compute_type", "int8")
        
        # Determine device - simplified to avoid GPU detection hanging
        if device_pref == "CPU Only":
            device = "cpu"
        elif device_pref == "CUDA GPU":
            device = "cuda"
        elif device_pref == "Metal GPU (Apple)":
            device = "auto"  # Let faster-whisper handle Metal detection
        else:  # Default to CPU for stability
            device = "cpu"
        
        core.log_message(f"Loading Whisper model ({core.WHISPER_MODEL_SIZE}) on {device} with {compute_type}...")
        
        try:
            whisper_model = WhisperModel(
                core.WHISPER_MODEL_SIZE, 
                device=device, 
                compute_type=compute_type,
                num_workers=1 if device == "cpu" else 4,  # More workers for GPU
                download_root=None,
                local_files_only=False
            )
            actual_device = getattr(whisper_model.model, 'device', 'unknown')
            core.log_message(f"Whisper model loaded on {actual_device} with {compute_type} precision.")
        except Exception as e:
            core.log_message(f"Failed to load on {device}, falling back to CPU: {e}", "WARNING")
            whisper_model = WhisperModel(
                core.WHISPER_MODEL_SIZE, 
                device="cpu", 
                compute_type="int8",
                num_workers=1
            )
            core.log_message("Whisper model loaded on CPU fallback.")
    
    return whisper_model

# --- Efficient Audio Resampling ---
def efficient_resample(audio, orig_sr, target_sr):
    """CPU-efficient audio resampling using scipy."""
    if orig_sr == target_sr:
        return audio
    
    # Calculate new length
    new_length = int(len(audio) * target_sr / orig_sr)
    
    # Use scipy resample (faster than librosa on CPU)
    try:
        resampled = resample(audio, new_length)
        return resampled.astype(np.float32)
    except Exception as e:
        core.log_message(f"Scipy resampling failed: {e}, falling back to simple interpolation", "WARNING")
        # Simple linear interpolation fallback
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

# Apply persisted timing/VAD preferences at startup (if present)
try:
    if isinstance(user_preferences, dict):
        # Whisper model size
        if "whisper_model_size" in user_preferences and hasattr(core, "WHISPER_MODEL_SIZE"):
            core.WHISPER_MODEL_SIZE = str(user_preferences["whisper_model_size"]).strip()
        if "block_duration_ms" in user_preferences:
            RUNTIME_PARAMS["block_duration_ms"] = int(user_preferences["block_duration_ms"])
        if "overlap_ms" in user_preferences:
            RUNTIME_PARAMS["overlap_s"] = float(user_preferences["overlap_ms"]) / 1000.0
        if "min_silence_ms" in user_preferences:
            RUNTIME_PARAMS["min_silence_s"] = float(user_preferences["min_silence_ms"]) / 1000.0
        if "min_speech_ms" in user_preferences:
            RUNTIME_PARAMS["min_speech_s"] = float(user_preferences["min_speech_ms"]) / 1000.0
        if "max_speech_s" in user_preferences:
            RUNTIME_PARAMS["max_speech_s"] = float(user_preferences["max_speech_s"])
        # VAD params
        if hasattr(core, "NO_SPEECH_THRESHOLD") and "no_speech_threshold" in user_preferences:
            core.NO_SPEECH_THRESHOLD = float(user_preferences["no_speech_threshold"])
        if hasattr(core, "VAD_FILTER") and "vad_filter" in user_preferences:
            core.VAD_FILTER = bool(user_preferences["vad_filter"])
        core.log_message(f"Applied saved preferences to runtime: whisper_model={getattr(core,'WHISPER_MODEL_SIZE',None)}, timing={RUNTIME_PARAMS}, no_speech={getattr(core,'NO_SPEECH_THRESHOLD',None)}, vad={getattr(core,'VAD_FILTER',None)}")
except Exception as e:
    core.log_message(f"Failed to apply saved timing/VAD preferences: {e}", "WARNING")

# --- Async Processing Variables ---
async_loop = None
tts_queue = queue.Queue()
tts_thread = None
tts_stop_event = threading.Event()

def get_event_loop():
    """Get or create an event loop for async operations."""
    global async_loop
    if async_loop is None or async_loop.is_closed():
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
    return async_loop

def tts_worker():
    """Worker thread for processing TTS requests with synchronization support."""
    global tts_stop_event
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while not tts_stop_event.is_set():
        try:
            # Get a TTS task from the queue with a timeout
            task = tts_queue.get(timeout=0.5)
            if task is None:
                tts_queue.task_done()
                continue
                
            translation, voice, settings, output_device_idx, result_queue = task
            
            # Apply audio output delay if configured
            audio_delay = float(user_preferences.get("audio_output_delay", 0.0))
            if audio_delay > 0:
                time.sleep(audio_delay)
            
            # Process TTS request - now returns None since audio is played directly
            try:
                loop.run_until_complete(core.text_to_speech_async(
                    translation, voice, settings, output_device_idx
                ))
                if result_queue is not None:
                    result_queue.put((True, "Audio played successfully"))
            except Exception as e:
                core.log_message(f"TTS worker error: {e}", "ERROR")
                if result_queue is not None:
                    result_queue.put((False, str(e)))
            
            tts_queue.task_done()
        except queue.Empty:
            # No tasks in queue, just continue
            pass
        except Exception as e:
            core.log_message(f"Error in TTS worker thread: {e}", "ERROR")
    
    loop.close()
    core.log_message("TTS worker thread stopped")

def start_tts_worker():
    """Start the TTS worker thread if not already running."""
    global tts_thread, tts_stop_event
    
    if tts_thread is None or not tts_thread.is_alive():
        tts_stop_event.clear()
        tts_thread = threading.Thread(target=tts_worker, daemon=True)
        tts_thread.start()
        core.log_message("TTS worker thread started")

# --- Audio Recording Functions ---
def record_audio(input_device_index, audio_q, stop_ev):
    """Records audio using sounddevice InputStream at the device's native rate and enqueues raw data for downstream resampling."""
    channels = 1
    dtype = "float32"

    try:
        # Resolve device and native samplerate
        device_to_use = None if input_device_index in (None, -1) else input_device_index
        try:
            dev_info = sd.query_devices(device_to_use)
            native_rate = int(dev_info.get("default_samplerate") or 48000)
        except Exception as e:
            core.log_message(f"Could not query device info ({input_device_index}): {e}. Falling back to 48000Hz", "WARNING")
            native_rate = 48000

        # Use runtime-configurable block duration
        block_ms = max(10, min(50, int(RUNTIME_PARAMS.get("block_duration_ms", 20))))
        blocksize = int(native_rate * block_ms / 1000)

        core.log_message(
            f"Attempting to open sounddevice InputStream on device {input_device_index} at native {native_rate}Hz (will resample to {core.TARGET_RATE}Hz)"
        )

        # Lightweight callback: enqueue (samples, sample_rate)
        def _cb(indata, frames, cb_time, status):
            if status:
                core.log_message(f"Audio Callback Status: {status}", "WARNING")
            try:
                data = indata.copy().flatten().astype(np.float32)
                audio_q.put((data, native_rate))
            except Exception as cb_e:
                core.log_message(f"Audio callback error: {cb_e}", "ERROR")

        with sd.InputStream(
            samplerate=native_rate,
            blocksize=blocksize,
            device=device_to_use,
            channels=channels,
            dtype=dtype,
            callback=_cb,
        ) as stream:
            core.log_message(
                f"Sounddevice InputStream started on device {input_device_index} at {native_rate}Hz."
            )
            
            while not stop_ev.is_set():
                time.sleep(0.1)

            core.log_message("Stop event received, stopping stream...")

    except Exception as e:
        core.log_message(f"Failed to open sounddevice stream: {e}", "ERROR")
    finally:
        core.log_message("Sounddevice InputStream stopped and closed.")
        if not stop_ev.is_set():
            core.log_message("Signaling stop due to recording error/exit.", "WARNING")
            stop_ev.set()


def audio_callback(indata, frames, time, status, audio_q):
    """Sounddevice callback: Called for each audio block."""
    if status:
        core.log_message(f"Audio Callback Status: {status}", "WARNING")
    audio_q.put(indata.copy())


def process_audio_chunk(audio_data, source_language, target_language, ollama_model, selected_voice):
    """Process a single audio chunk for the Gradio interface."""
    # Use singleton Whisper model
    whisper_model = get_whisper_model()
    
    # Convert audio data to numpy array if needed
    if isinstance(audio_data, dict) and "array" in audio_data:
        audio_data = audio_data["array"]
    # If browser gave 2D (samples, channels), make mono
    try:
        if hasattr(audio_data, "ndim") and audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
    except Exception:
        pass
    
    # Ensure audio is float32
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    
    # Normalize if needed
    max_val = np.max(np.abs(audio_data))
    if max_val > 1.0:
        audio_data = audio_data / max_val
    
    # Transcribe
    transcription, detected_code = core.transcribe_audio(
        audio_data, source_language, whisper_model
    )
    
    if not transcription:
        return None, None, None
    
    # Determine actual source language name for the prompt
    if source_language == "Auto-Detect":
        actual_source_lang_name = core.CODE_TO_LANGUAGE.get(
            detected_code, "English"
        )
    else:
        actual_source_lang_name = source_language
    
    # Translate
    translation = core.translate(
        transcription,
        actual_source_lang_name,
        target_language,
        ollama_model,
        current_settings
    )
    
    if not translation:
        return transcription, None, None
    
    # Generate speech using the shared event loop - audio plays directly, no file returned
    loop = get_event_loop()
    loop.run_until_complete(core.text_to_speech_async(
        translation, 
        selected_voice,
        current_settings
    ))
    
    return transcription, translation, None


def get_audio_devices():
    """Gets list of available audio input and output devices with platform-specific handling."""
    input_devices = []
    output_devices = []
    default_input_idx = -1
    default_output_idx = -1
    
    # Try to detect platform
    platform = "linux"  # Default
    try:
        if os.path.exists("/app/platform.txt"):
            with open("/app/platform.txt", "r") as f:
                platform = f.read().strip()
            core.log_message(f"Detected platform from file: {platform}")
        else:
            # Fallback platform detection
            if os.name == 'nt':
                platform = "windows"
            elif os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
                platform = "macos"
            core.log_message(f"Detected platform from system: {platform}")
    except Exception as e:
        core.log_message(f"Error detecting platform: {e}. Using default: {platform}", "WARNING")
    
    try:
        devices = sd.query_devices()
        default_indices = sd.default.device
        default_input_idx = default_indices[0]
        default_output_idx = default_indices[1]
        
        core.log_message(f"Found {len(devices)} audio devices on {platform}. Default input: {default_input_idx}, Default output: {default_output_idx}")

        # Platform-specific device filtering
        for i, dev in enumerate(devices):
            try:
                hostapi_info = sd.query_hostapis(dev["hostapi"])
                hostapi_name = hostapi_info["name"] if hostapi_info else "N/A"
            except Exception:
                hostapi_name = "Error"

            device_name = f"{i}: {dev['name']} ({hostapi_name})"

            # Skip JACK devices to avoid stalls when JACK graph isn't configured
            name_lower = (dev.get("name", "") or "").lower()
            if "jack" in name_lower or "jack" in hostapi_name.lower():
                core.log_message(f"Skipping JACK device due to stability concerns: {device_name}", "WARNING")
                continue
            
            # Check if device supports input
            if dev.get("max_input_channels", 0) > 0:
                try:
                    # Platform-specific input device checks
                    if platform == "macos" and "Built-in" in dev.get("name", ""):
                        # Prioritize built-in devices on macOS
                        core.log_message(f"Prioritizing macOS built-in input device: {device_name}")
                        input_devices.insert(0, (device_name, i))
                    elif platform == "windows" and ("Microphone" in dev.get("name", "") or "Input" in dev.get("name", "")):
                        # Prioritize common input devices on Windows
                        core.log_message(f"Prioritizing Windows input device: {device_name}")
                        input_devices.insert(0, (device_name, i))
                    else:
                        # Do not enforce 16kHz; accept and resample downstream
                        input_devices.append((device_name, i))
                        core.log_message(f"Added input device: {device_name}")
                except Exception as e:
                    core.log_message(f"Input device {device_name} (Index: {i}) listing error: {e}", "WARNING")
            
            # Check if device supports output
            if dev.get("max_output_channels", 0) > 0:
                # Platform-specific output device checks
                if platform == "macos" and "Built-in" in dev.get("name", ""):
                    # Prioritize built-in devices on macOS
                    core.log_message(f"Prioritizing macOS built-in output device: {device_name}")
                    output_devices.insert(0, (device_name, i))
                elif platform == "windows" and ("Speakers" in dev.get("name", "") or "Output" in dev.get("name", "")):
                    # Prioritize common output devices on Windows
                    core.log_message(f"Prioritizing Windows output device: {device_name}")
                    output_devices.insert(0, (device_name, i))
                else:
                    output_devices.append((device_name, i))
                    core.log_message(f"Added output device: {device_name}")
    except Exception as e:
        core.log_message(f"Error querying sound devices: {e}", "ERROR")
        # Add virtual devices as fallback
        if not input_devices:
            input_devices = [("Virtual Microphone (Fallback)", -1)]
            core.log_message("Added fallback virtual microphone")
        if not output_devices:
            output_devices = [("Virtual Speaker (Fallback)", -1)]
            core.log_message("Added fallback virtual speaker")
        return input_devices, output_devices, -1, -1

    # Ensure default indices are valid
    if default_input_idx != -1 and not any(idx == default_input_idx for _, idx in input_devices):
        default_input_idx = input_devices[0][1] if input_devices else -1
    
    if default_output_idx != -1 and not any(idx == default_output_idx for _, idx in output_devices):
        default_output_idx = output_devices[0][1] if output_devices else -1
    
    # Add virtual devices at the end as last resort options
    input_devices.append(("Virtual Microphone (Fallback)", -1))
    output_devices.append(("Virtual Speaker (Fallback)", -1))
        
    return input_devices, output_devices, default_input_idx, default_output_idx


# --- Gradio Interface Functions ---
def process_audio(audio, source_language, target_language, ollama_model, voice):
    """Process audio from Gradio's audio input."""
    if audio is None:
        return "No audio detected", "", None

    # Accept either (sample_rate, data) or raw numpy array/dict from browser
    audio_data = None
    if isinstance(audio, tuple) and len(audio) == 2:
        sample_rate, audio_data = audio
    else:
        sample_rate = None
        audio_data = audio
    if audio_data is None:
         return "No audio data received", "", None
    
    # Ensure TTS worker is running
    start_tts_worker()
    
    # Use singleton Whisper model
    whisper_model = get_whisper_model()
    
    # Convert audio data to numpy array if needed
    if isinstance(audio_data, dict) and "array" in audio_data:
        audio_data = audio_data["array"]
    
    # Ensure audio is float32
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    
    # Normalize if needed
    max_val = np.max(np.abs(audio_data))
    if max_val > 1.0:
        audio_data = audio_data / max_val
    
    # Transcribe
    transcription, detected_code = core.transcribe_audio(
        audio_data, source_language, whisper_model
    )
    
    if not transcription:
        return "No speech detected", "", None
    
    # Determine actual source language name for the prompt
    if source_language == "Auto-Detect":
        actual_source_lang_name = core.CODE_TO_LANGUAGE.get(
            detected_code, "English"
        )
    else:
        actual_source_lang_name = source_language
    
    # Translate
    translation = core.translate(
        transcription,
        actual_source_lang_name,
        target_language,
        ollama_model,
        current_settings
    )
    
    if not translation:
        return transcription, "Translation failed", None
    
    # Create a result queue for this specific TTS request
    result_queue = queue.Queue()
    
    # Add TTS task to queue
    tts_queue.put((
        translation, 
        voice,
        current_settings,
        None,  # No output device for browser playback
        result_queue
    ))
    
    # Wait for result with a timeout
    try:
        success, result = result_queue.get(timeout=5.0)
        result_queue.task_done()
        
        if success:
            # Audio was played successfully, no file to return
            pass
        else:
            core.log_message(f"TTS error: {result}", "ERROR")
    except queue.Empty:
        core.log_message("TTS request timed out", "WARNING")
    
    # Return transcription and translation, no audio file since it's streamed
    return transcription, translation, None


def start_continuous_recording(source_language, target_language, ollama_model, voice, device_idx):
    """Start continuous recording for real-time translation."""
    global recording_thread, stop_event
    
    if recording_thread and recording_thread.is_alive():
        return "Recording is already in progress."
    
    # Ensure TTS worker is running before starting recording
    start_tts_worker()
    
    stop_event.clear()
    
    # Start recording thread
    recording_thread = threading.Thread(
        target=record_audio,
        args=(device_idx, audio_queue, stop_event),
        daemon=True
    )
    recording_thread.start()
    
    return "Started continuous recording. Speak now..."


def stop_continuous_recording():
    """Stop the continuous recording."""
    global recording_thread, stop_event
    
    if not recording_thread or not recording_thread.is_alive():
        return "No recording in progress."
    
    stop_event.set()
    recording_thread.join(timeout=2.0)
    
    return "Recording stopped."


# --- Audio Processing State Variables ---
audio_buffer = CircularAudioBuffer(max_duration_seconds=20)  # Use circular buffer
silence_counter = 0.0
is_speaking = False
last_transcription = ""

def check_audio_queue(source_language, target_language, ollama_model, voice, output_device=None):
    """Check for new audio in the queue and process it using sophisticated buffer management."""
    core.log_message(f"Checking audio queue with params: {source_language}, {target_language}, {ollama_model}, {voice}, {output_device}")
    
    global audio_buffer, silence_counter, is_speaking, last_transcription, whisper_model
    
    # Timing parameters driven by runtime settings
    MIN_SILENCE_DURATION = float(RUNTIME_PARAMS.get("min_silence_s", 0.6))
    MIN_SPEECH_DURATION = float(RUNTIME_PARAMS.get("min_speech_s", 1.0))
    MAX_SPEECH_DURATION = float(RUNTIME_PARAMS.get("max_speech_s", 10.0))
    BUFFER_OVERLAP = float(RUNTIME_PARAMS.get("overlap_s", 0.5))
    MIN_SPEECH_SIZE = int(core.TARGET_RATE * MIN_SPEECH_DURATION)
    MAX_SPEECH_SIZE = int(core.TARGET_RATE * MAX_SPEECH_DURATION)
    OVERLAP_SIZE = int(core.TARGET_RATE * BUFFER_OVERLAP)
    
    # Get output device index if provided
    output_device_idx = None
    if output_device:
        for name, idx in output_devices:
            if name == output_device:
                output_device_idx = idx
                break
    
    # Use singleton Whisper model
    whisper_model = get_whisper_model()
    
    # Ensure TTS worker is running
    start_tts_worker()
    
    # Check if there are new audio chunks in the queue
    if audio_queue.empty():
        # No new audio, check if we should process the buffer due to silence timeout
        if not is_speaking and audio_buffer.data_size > MIN_SPEECH_SIZE and silence_counter > MIN_SILENCE_DURATION:
            core.log_message("Processing due to silence timeout.", "DEBUG")
            buffer_audio = audio_buffer.get_audio()
            transcription, detected_code = core.transcribe_audio(
                buffer_audio, source_language, whisper_model
            )
            
            if transcription and transcription != last_transcription:
                # Determine actual source language name for the prompt
                if source_language == "Auto-Detect":
                    actual_source_lang_name = core.CODE_TO_LANGUAGE.get(
                        detected_code, "English"
                    )
                else:
                    actual_source_lang_name = source_language
                
                # Translate
                translation = core.translate(
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    current_settings
                )
                
                if translation:
                    # Fire-and-forget: enqueue TTS and continue without waiting
                    tts_queue.put((
                        translation, 
                        voice,
                        current_settings,
                        output_device_idx,
                        None
                    ))
                    
                    # Keep buffer continuity - only clear if buffer is too large
                    if audio_buffer.data_size > MAX_SPEECH_SIZE:
                        overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
                        audio_buffer.clear()
                        if len(overlap_audio) > 0:
                            audio_buffer.add_audio(overlap_audio)
                    
                    # Reset speaking state but maintain buffer for continuity
                    is_speaking = False
                    silence_counter = 0.0
                    last_transcription = transcription
                    
                    # Apply text display delay if configured
                    text_delay = float(user_preferences.get("text_display_delay", 0.0))
                    if text_delay > 0:
                        import threading
                        def delayed_return():
                            time.sleep(text_delay)
                        # For real-time, we return immediately but could log the delay
                        pass
                    elif text_delay < 0:
                        # Negative delay means show text early - already handled by immediate return
                        pass
                    
                    # Return text immediately; audio plays asynchronously
                    return transcription, translation, None
            
            # Only reset buffer if it's getting too large, otherwise keep for continuity
            if audio_buffer.data_size > MAX_SPEECH_SIZE:
                audio_buffer.clear()
                is_speaking = False
                silence_counter = 0.0
        elif not is_speaking:
            # Increment silence counter if not speaking
            silence_counter += 0.05  # Assuming check interval is ~50ms
        
        return None, None, None
    
    # Collect audio chunks from the queue
    chunks = []
    try:
        while True:
            chunk = audio_queue.get_nowait()
            chunks.append(chunk)
            audio_queue.task_done()
    except queue.Empty:
        pass
    
    if not chunks:
        return None, None, None
    
    # Prepare and resample chunks to TARGET_RATE if needed, then combine
    resampled_chunks = []
    for ch in chunks:
        try:
            if isinstance(ch, tuple) and len(ch) == 2:
                data, sr = ch
            else:
                data, sr = ch, core.TARGET_RATE
            data = np.asarray(data, dtype=np.float32).flatten()
            if sr != core.TARGET_RATE:
                try:
                    data = efficient_resample(data, int(sr), core.TARGET_RATE)
                except Exception as re:
                    core.log_message(f"Processing resample {sr}->{core.TARGET_RATE} failed: {re}", "WARNING")
                    continue
            resampled_chunks.append(data)
        except Exception as ce:
            core.log_message(f"Error preparing audio chunk: {ce}", "ERROR")
    if not resampled_chunks:
        return None, None, None
    audio_chunk = np.concatenate(resampled_chunks).flatten().astype(np.float32)
    actual_duration = len(audio_chunk) / core.TARGET_RATE
    
    # Check if this is speech using configured energy threshold
    try:
        min_energy = float(user_preferences.get("speech_energy_threshold", 0.0008))
    except Exception:
        min_energy = 0.0008
    if core.is_speech(audio_chunk, min_threshold=min_energy):
        if not is_speaking:
            core.log_message("Speech detected...", "DEBUG")
            is_speaking = True
        
        silence_counter = 0.0
        audio_buffer.add_audio(audio_chunk)
        
        # Check if we've reached max buffer size
        if audio_buffer.data_size >= MAX_SPEECH_SIZE:
            core.log_message("Max buffer size reached, processing...", "DEBUG")
            buffer_audio = audio_buffer.get_audio()
            transcription, detected_code = core.transcribe_audio(
                buffer_audio, source_language, whisper_model
            )
            
            if transcription and transcription != last_transcription:
                # Determine actual source language name for the prompt
                if source_language == "Auto-Detect":
                    actual_source_lang_name = core.CODE_TO_LANGUAGE.get(
                        detected_code, "English"
                    )
                else:
                    actual_source_lang_name = source_language
                
                # Translate
                translation = core.translate(
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    current_settings
                )
                
                if translation:
                    # Fire-and-forget: enqueue TTS and continue without waiting
                    tts_queue.put((
                        translation, 
                        voice,
                        current_settings,
                        output_device_idx,
                        None
                    ))
                    
                    # Keep a portion of the buffer for overlap to prevent word loss
                    overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
                    audio_buffer.clear()
                    if len(overlap_audio) > 0:
                        audio_buffer.add_audio(overlap_audio)
                    
                    last_transcription = transcription
                    
                    # Apply text display delay if configured
                    text_delay = float(user_preferences.get("text_display_delay", 0.0))
                    if text_delay > 0:
                        import threading
                        def delayed_return():
                            time.sleep(text_delay)
                        # For real-time, we return immediately but could log the delay
                        pass
                    elif text_delay < 0:
                        # Negative delay means show text early - already handled by immediate return
                        pass
                    
                    # Return text immediately; audio plays asynchronously
                    return transcription, translation, None
            
            # Keep a portion of the buffer for overlap to prevent word loss
            overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
            audio_buffer.clear()
            if len(overlap_audio) > 0:
                audio_buffer.add_audio(overlap_audio)
    
    elif is_speaking:
        # This chunk is silence but we were speaking before
        silence_counter += actual_duration
        audio_buffer.add_audio(audio_chunk)
        
        # Check if we've had enough silence after speech
        if silence_counter >= MIN_SILENCE_DURATION and audio_buffer.data_size >= MIN_SPEECH_SIZE:
            core.log_message("End of speech detected, processing...", "DEBUG")
            buffer_audio = audio_buffer.get_audio()
            transcription, detected_code = core.transcribe_audio(
                buffer_audio, source_language, whisper_model
            )
            
            if transcription and core.is_complete_sentence(transcription) and transcription != last_transcription:
                # Determine actual source language name for the prompt
                if source_language == "Auto-Detect":
                    actual_source_lang_name = core.CODE_TO_LANGUAGE.get(
                        detected_code, "English"
                    )
                else:
                    actual_source_lang_name = source_language
                
                # Translate
                translation = core.translate(
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    current_settings
                )
                
                if translation:
                    # Fire-and-forget: enqueue TTS and continue without waiting
                    tts_queue.put((
                        translation, 
                        voice,
                        current_settings,
                        output_device_idx,
                        None
                    ))
                    
                    # Keep a portion of the buffer for overlap to prevent word loss
                    overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
                    audio_buffer.clear()
                    if len(overlap_audio) > 0:
                        audio_buffer.add_audio(overlap_audio)
                # Keep a portion of the buffer for overlap to prevent word loss
                overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
                audio_buffer.clear()
                if len(overlap_audio) > 0:
                    audio_buffer.add_audio(overlap_audio)
                    
                is_speaking = False
                silence_counter = 0.0
    else:
        # Not speech and not speaking, just increment silence counter
        silence_counter += actual_duration
    
    return None, None, None


# --- Gradio UI Setup ---
def create_ui():
    """Create the Gradio web interface."""
    # Get available audio devices
    global input_devices, output_devices
    input_devices, output_devices, default_input_idx, default_output_idx = get_audio_devices()
    input_device_names = [name for name, _ in input_devices]
    output_device_names = [name for name, _ in output_devices]

    # Set default input device safely - check saved preferences first
    default_input_name = user_preferences.get("input_device")
    if not default_input_name or default_input_name not in input_device_names:
        if input_device_names: # Check if list is not empty
            if default_input_idx != -1:
                for name, idx in input_devices:
                    if idx == default_input_idx:
                        default_input_name = name
                        break
            # If default not found or invalid, or no default index, pick first available
            if default_input_name is None:
                 default_input_name = input_device_names[0]

    # Set default output device safely - check saved preferences first
    default_output_name = user_preferences.get("output_device")
    if not default_output_name or default_output_name not in output_device_names:
        if output_device_names: # Check if list is not empty
            if default_output_idx != -1:
                for name, idx in output_devices:
                    if idx == default_output_idx:
                        default_output_name = name
                        break
            # If default not found or invalid, or no default index, pick first available
            if default_output_name is None:
                 default_output_name = output_device_names[0]

    with gr.Blocks(title="GoGospleNow.com", theme=gr.themes.Soft()) as app:
        gr.Markdown("# GoGospleNow.com")
        gr.Markdown("Real Time Preaching Translator")

        # --- Status Indicator (Server Ready Light) ---
        # Minimal CSS for the dot indicator
        gr.HTML(
            """
            <style>
            .status-wrap { display: flex; align-items: center; gap: 10px; }
            .status-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
            .ok { background: #16a34a; box-shadow: 0 0 6px #16a34a; }
            .bad { background: #dc2626; box-shadow: 0 0 6px #dc2626; }
            .warn { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }
            .status-text { font-weight: 600; }
            </style>
            """
        )
        status_indicator = gr.HTML(
            value='<div class="status-wrap"><span class="status-dot bad"></span><span class="status-text">Starting…</span></div>',
            label="Server Status"
        )
        status_timer = gr.Timer(1.0, active=True)

        def ui_status():
            """Assemble concise HTML status based on backend/service state."""
            try:
                status = core.get_status()
            except Exception as e:
                core.log_message(f"Status error: {e}", "ERROR")
                status = {"ollama_ok": False, "tts_ok": False, "services_ok": False, "transcribing": False, "detail": str(e)}

            # Local runtime states
            w_loaded = whisper_model is not None
            tts_alive = (tts_thread is not None and tts_thread.is_alive())
            rec_alive = (recording_thread is not None and recording_thread.is_alive())

            # Consider the system "ready" only when we are actively recording
            ready = bool(w_loaded and tts_alive and status.get("services_ok", False) and rec_alive)
            transcribing = bool(status.get("transcribing", False))

            if transcribing and ready:
                dot_class = "warn"
                text = "Transcribing…"
            elif ready:
                dot_class = "ok"
                text = "Ready for transcription"
            else:
                dot_class = "bad"
                # Build a short reason
                reasons = []
                if not w_loaded:
                    reasons.append("Whisper not loaded")
                if not tts_alive:
                    reasons.append("TTS worker not running")
                if not status.get("services_ok", False):
                    detail = status.get("detail", "Services not ready")
                    reasons.append(detail)
                if not rec_alive:
                    reasons.append("Recording stopped")
                # Recording thread being off is not necessarily an error
                text = "Not ready: " + "; ".join([r for r in reasons if r]) if reasons else "Not ready"

            html = f'<div class="status-wrap"><span class="status-dot {dot_class}"></span><span class="status-text">{text}</span></div>'
            return html

        status_timer.tick(fn=ui_status, outputs=status_indicator, show_progress=False)
        
        # Create main interface
        with gr.Tab("Speech Translator"):
            # Store default device indices for use in functions
            input_device_idx = default_input_idx if default_input_idx != -1 else 0
            output_device_idx = default_output_idx if default_output_idx != -1 else 0
            
            with gr.Row():
                with gr.Column(scale=1):
                    
                    with gr.Row():
                        # Ensure saved language preferences are valid; if not, fall back to first choice
                        src_choices = core.SOURCE_LANGUAGES
                        tgt_choices = core.TARGET_LANGUAGES
                        saved_src = user_preferences.get("source_language", src_choices[0] if src_choices else "")
                        saved_tgt = user_preferences.get("target_language", tgt_choices[0] if tgt_choices else "")
                        default_src = saved_src if saved_src in src_choices else (src_choices[0] if src_choices else "")
                        default_tgt = saved_tgt if saved_tgt in tgt_choices else (tgt_choices[0] if tgt_choices else "")

                        cont_source_language = gr.Dropdown(
                            choices=src_choices,
                            value=default_src,
                            label="Source Language"
                        )
                        
                        cont_target_language = gr.Dropdown(
                            choices=tgt_choices,
                            value=default_tgt,
                            label="Translation Target Language"
                        )
                    
                    with gr.Row():
                        default_model = user_preferences.get("ollama_model", "")
                        if not default_model and available_ollama_models:
                            default_model = available_ollama_models[0]
                            
                        cont_ollama_model = gr.Dropdown(
                            choices=available_ollama_models,
                            value=default_model,
                            label="AI Translation Model",
                            allow_custom_value=True
                        )
                        
                        # Build labeled choices for voices without changing their underlying values
                        voice_country_map = {
                            # United States
                            "af_heart": "United States", "af_alloy": "United States", "af_aoede": "United States",
                            "af_bella": "United States", "af_jessica": "United States", "af_kore": "United States",
                            "af_nicole": "United States", "af_nova": "United States", "af_river": "United States",
                            "af_sarah": "United States", "af_sky": "United States", "am_adam": "United States",
                            "am_echo": "United States", "am_eric": "United States", "am_fenrir": "United States",
                            "am_liam": "United States", "am_michael": "United States", "am_onyx": "United States",
                            "am_puck": "United States", "am_santa": "United States",
                            # United Kingdom
                            "bf_alice": "United Kingdom", "bf_emma": "United Kingdom", "bf_isabella": "United Kingdom",
                            "bf_lily": "United Kingdom", "bm_daniel": "United Kingdom", "bm_fable": "United Kingdom",
                            "bm_george": "United Kingdom", "bm_lewis": "United Kingdom",
                            # Japan
                            "jf_alpha": "Japan", "jf_gongitsune": "Japan", "jf_nezumi": "Japan", "jf_tebukuro": "Japan",
                            "jm_kumo": "Japan",
                            # China
                            "zf_xiaobei": "China", "zf_xiaoni": "China", "zf_xiaoxiao": "China", "zf_xiaoyi": "China",
                            "zm_yunjian": "China", "zm_yunxi": "China", "zm_yunxia": "China", "zm_yunyang": "China",
                            # Spain
                            "ef_dora": "Spain", "em_alex": "Spain", "em_santa": "Spain",
                            # France
                            "ff_siwis": "France",
                            # India
                            "hf_alpha": "India", "hf_beta": "India", "hm_omega": "India", "hm_psi": "India",
                            # Italy
                            "if_sara": "Italy", "im_nicola": "Italy",
                            # Brazil
                            "pf_dora": "Brazil", "pm_alex": "Brazil", "pm_santa": "Brazil",
                        }
                        # Only include voices present in core.KOKORO_VOICES to avoid mismatches
                        labeled_voice_choices = [
                            (f"{v} — {voice_country_map.get(v, 'Unknown')}", v)
                            for v in core.KOKORO_VOICES
                        ]

                        cont_voice = gr.Dropdown(
                            choices=labeled_voice_choices,
                            value=user_preferences.get("voice", "em_alex"),
                            label="Audio Output Voice",
                            info="Should match Translation Target Language"
                        )
                    
                    with gr.Row():
                        cont_input_device = gr.Dropdown(
                            choices=input_device_names,
                            value=default_input_name,
                            label="Input Device (Microphone)"
                        )
                        
                        cont_output_device = gr.Dropdown(
                            choices=output_device_names,
                            value=default_output_name,
                            label="Output Device (Speaker)"
                        )
                    
                    with gr.Row():
                        start_btn = gr.Button("Start Translation", variant="primary")
                        stop_btn = gr.Button("Stop Translation", interactive=False)
                    
                with gr.Column(scale=1):
                    cont_transcription = gr.Textbox(label="Transcription", lines=5)
                    cont_translation = gr.Textbox(label="Translation", lines=5)
            
            # Modified to use selected device
            def start_with_selected_device(source_lang, target_lang, model, voice_choice, input_device_name, output_device_name):
                try:
                    # Find input device index from name
                    selected_input_idx = input_device_idx  # fallback
                    for name, idx in input_devices:
                        if name == input_device_name:
                            selected_input_idx = idx
                            break
                    
                    # Find output device index from name
                    selected_output_idx = output_device_idx  # fallback
                    for name, idx in output_devices:
                        if name == output_device_name:
                            selected_output_idx = idx
                            break
                    
                    core.log_message(f"Using input device: {input_device_name} (index: {selected_input_idx})")
                    core.log_message(f"Using output device: {output_device_name} (index: {selected_output_idx})")
                    
                    # Store selected output device globally for TTS
                    global selected_output_device_name
                    selected_output_device_name = output_device_name
                    
                    return start_continuous_recording(source_lang, target_lang, model, voice_choice, selected_input_idx)
                except Exception as e:
                    core.log_message(f"Error starting recording: {e}", "ERROR")
                    return f"Error starting recording: {e}"
            
            # Function to save preferences when starting recording
            def start_and_save_prefs(source_lang, target_lang, model, voice_choice, input_device_name, output_device_name):
                # Save preferences including device selections
                global user_preferences
                user_preferences.update({
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "ollama_model": model,
                    "voice": voice_choice,
                    "input_device": input_device_name,
                    "output_device": output_device_name
                })
                save_user_preferences(user_preferences)
                
                # Start recording with selected device
                result = start_with_selected_device(source_lang, target_lang, model, voice_choice, input_device_name, output_device_name)
                if not result.startswith("Error"):
                    return [gr.Button(interactive=False), gr.Button(interactive=True), gr.update(active=True)]
                return [gr.Button(interactive=True), gr.Button(interactive=False), gr.update(active=False)]
            
            # Server-side polling via Gradio Timer (avoids relying on browser JS)
            continuous_timer = gr.Timer(0.2, active=False)

            start_btn.click(
                fn=start_and_save_prefs,
                inputs=[cont_source_language, cont_target_language, cont_ollama_model, cont_voice, cont_input_device, cont_output_device],
                outputs=[start_btn, stop_btn, continuous_timer],
                show_progress=False
            )
            
            def stop_and_update_buttons():
                stop_continuous_recording()
                return [gr.Button(interactive=True), gr.Button(interactive=False), gr.update(active=False)]
            
            stop_btn.click(
                fn=stop_and_update_buttons,
                inputs=[],
                outputs=[start_btn, stop_btn, continuous_timer],
                show_progress=False
            )
            
            # Keep track of the last valid transcription and translation
            last_valid_transcription = ""
            last_valid_translation = ""
            
            # Function to update UI with new translations
            def continuous_update(source_lang, target_lang, model, voice_choice):
                nonlocal last_valid_transcription, last_valid_translation
                core.log_message(f"Continuous update called with: {source_lang}, {target_lang}, {model}, {voice_choice}")
                try:
                    transcription, translation, audio_file = check_audio_queue(
                        source_lang, target_lang, model, voice_choice, selected_output_device_name
                    )
                    
                    # Sticky UI logic to avoid clearing boxes on transient None/empty values
                    if transcription is None and (translation is None or translation == ""):
                        core.log_message("Sticky UI: no new transcription/translation; keeping last shown values", "DEBUG")
                        return last_valid_transcription, last_valid_translation

                    # Determine what to display and what to persist as last valid
                    out_transcription = last_valid_transcription
                    out_translation = last_valid_translation

                    if transcription is not None and transcription != "":
                        out_transcription = transcription
                        # Persist new non-empty transcription
                        last_valid_transcription = transcription
                    else:
                        core.log_message("Sticky UI: transcription missing/empty; preserving previous transcription", "DEBUG")

                    if translation is not None and translation != "":
                        out_translation = translation
                        # Persist new non-empty translation
                        last_valid_translation = translation
                    else:
                        core.log_message("Sticky UI: translation missing/empty; preserving previous translation", "DEBUG")

                    # Log translation to file only when we have new non-empty values
                    if transcription:
                        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                        with open("translation_log.txt", "a", encoding="utf-8") as f:
                            f.write(f"[{current_time}]\nSource: {transcription}\nTranslation: {translation if translation else out_translation}\n\n")

                    core.log_message(
                        f"Continuous update returning: {out_transcription[:30]}..., {out_translation[:30] if out_translation else None}",
                        "DEBUG",
                    )
                    return out_transcription, out_translation
                except Exception as e:
                    core.log_message(f"Error in continuous update: {e}", "ERROR")
                    return f"Error: {str(e)}", last_valid_translation
            
            # Set up continuous updates
            continuous_update_interval = 200  # milliseconds - reduced for more responsive UI

            # Register timer tick AFTER defining continuous_update to avoid UnboundLocalError
            continuous_timer.tick(
                fn=continuous_update,
                inputs=[cont_source_language, cont_target_language, cont_ollama_model, cont_voice],
                outputs=[cont_transcription, cont_translation],
                show_progress=False
            )
            
            # Remove reliance on browser JS polling; Timer handles server-side polling

        # Browser microphone tab removed per user request
        
        with gr.Tab("Settings"):
            gr.Markdown("## Server Settings")
            gr.Markdown("Tip: Hover the ⓘ icons next to each control for guidance.")
            
            with gr.Row():
                translation_server = gr.Textbox(
                    value=current_settings.get("translation_server", core.DEFAULT_SETTINGS["translation_server"]),
                    label="Translation Server URL",
                    info="Base URL for your Ollama server (e.g., http://localhost:11434)."
                )
                
                tts_server = gr.Textbox(
                    value=current_settings.get("tts_server_url", core.DEFAULT_SETTINGS["tts_server_url"]),
                    label="TTS Server URL",
                    info="Base URL for the Kokoro TTS API (e.g., http://localhost:8880/v1)."
                )
            
            def save_settings(translation_url, tts_url):
                new_settings = {
                    "translation_server": translation_url,
                    "tts_server_url": tts_url
                }
                
                try:
                    with open(core.SETTINGS_FILE, "w") as f:
                        json.dump(new_settings, f, indent=4)
                    
                    global current_settings
                    current_settings = new_settings
                    
                    # Refresh Ollama models
                    global available_ollama_models
                    available_ollama_models = core.fetch_ollama_models(translation_url)
                    
                    return f"Settings saved successfully. Found {len(available_ollama_models)} Ollama models."
                except Exception as e:
                    return f"Error saving settings: {e}"
            
            save_btn = gr.Button("Save Server Settings")
            settings_status = gr.Textbox(label="Status")
            
            save_btn.click(
                fn=save_settings,
                inputs=[translation_server, tts_server],
                outputs=[settings_status]
            )

            gr.Markdown("---")
            gr.Markdown("## 🎯 Performance Optimization & VAD Settings")

            # Timing and Overlap Settings
            with gr.Row():
                s_block_ms = gr.Slider(minimum=10, maximum=50, step=1,
                                       value=int(RUNTIME_PARAMS["block_duration_ms"]),
                                       label="Audio Block Duration (ms)",
                                       info="Shorter = lower latency, more CPU. Longer = higher latency, less CPU.")
                s_overlap_ms = gr.Slider(minimum=200, maximum=1000, step=50,
                                         value=int(RUNTIME_PARAMS["overlap_s"] * 1000),
                                         label="Overlap After Processing (ms)",
                                         info="Audio kept after processing to avoid clipping words. More overlap = smoother, slightly more work.")
            with gr.Row():
                s_min_silence_ms = gr.Slider(minimum=300, maximum=1200, step=50,
                                              value=int(RUNTIME_PARAMS["min_silence_s"] * 1000),
                                              label="Min Silence To Finalize (ms)",
                                              info="Silence required after speech to finalize a segment. Higher = fewer, longer segments.")
                s_min_speech_ms = gr.Slider(minimum=800, maximum=2000, step=50,
                                             value=int(RUNTIME_PARAMS["min_speech_s"] * 1000),
                                             label="Min Speech To Start (ms)",
                                             info="Minimum speech duration before considered speech. Higher = fewer false starts.")
            with gr.Row():
                s_max_speech_s = gr.Slider(minimum=6, maximum=20, step=1,
                                            value=float(RUNTIME_PARAMS["max_speech_s"]),
                                            label="Max Utterance Duration (s)",
                                            info="Hard cap for a single utterance. Lower values cut long monologues sooner.")
            
            # VAD Settings
            with gr.Row():
                s_no_speech = gr.Slider(
                    minimum=0.4, maximum=1.2, step=0.05,
                    value=float(user_preferences.get("no_speech_threshold", getattr(core, "NO_SPEECH_THRESHOLD", 0.7))),
                    label="Whisper No-speech Threshold (higher = stricter)",
                    info="Higher = stricter silence detection (drops low-energy noise). Too high may miss quiet speech."
                )
                s_vad_filter = gr.Checkbox(
                    value=bool(user_preferences.get("vad_filter", getattr(core, "VAD_FILTER", False))),
                    label="Enable Whisper VAD Filter",
                    info="Let Whisper filter non-speech. On some systems it may drop soft speech—disable if you miss words."
                )
            
            gr.Markdown(
                "**Timing**: Block duration affects latency. Silence/speech thresholds control when processing starts/stops.\n"
                "**VAD**: No-speech threshold filters out non-speech. VAD filter may drop soft speech on some systems."
            )

            gr.Markdown("---")
            gr.Markdown("## 🖥️ CPU Performance Controls")
            
            with gr.Row():
                s_cpu_threads = gr.Slider(
                    minimum=1, maximum=12, step=1,
                    value=int(user_preferences.get("cpu_threads", 2)),
                    label="CPU Threads (lower = less CPU usage)",
                    info="Threads for compute libs. Lower = less CPU use; higher = faster on multi-core CPUs."
                )
                s_processing_batch = gr.Slider(
                    minimum=1, maximum=5, step=1,
                    value=int(user_preferences.get("processing_batch_size", 1)),
                    label="Audio Batch Size (higher = more efficient, higher latency)",
                    info="Process multiple chunks together. Higher = more efficient, slightly higher latency."
                )
            
            with gr.Row():
                s_buffer_size = gr.Slider(
                    minimum=10, maximum=60, step=5,
                    value=int(user_preferences.get("buffer_duration_s", 20)),
                    label="Audio Buffer Duration (s)",
                    info="Max running buffer length for detection. Longer = more context but more memory."
                )
                s_energy_threshold = gr.Slider(
                    minimum=0.0001, maximum=0.01, step=0.0001,
                    value=float(user_preferences.get("speech_energy_threshold", 0.0008)),
                    label="Speech Energy Threshold",
                    info="Lower to catch quieter speech; higher to reduce noise. Too low may detect noise as speech."
                )
            
            gr.Markdown(
                "**CPU**: Lower threads = less CPU usage. Higher batch size = more efficient but higher latency.\n"
                "**Buffer**: Longer duration = more context but uses more RAM. Energy threshold controls speech detection sensitivity."
            )
            
            gr.Markdown("---")
            gr.Markdown("## 🧠 Whisper Model Settings")
            
            # Whisper Model Size Selection
            with gr.Row():
                whisper_model_dropdown = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                    value=user_preferences.get("whisper_model_size", getattr(core, "WHISPER_MODEL_SIZE", "base")),
                    label="Whisper Model Size",
                    info="Larger models = better accuracy, slower. 'small' is a good balance."
                )

            # GPU Detection and Settings
            with gr.Row():
                device_dropdown = gr.Dropdown(
                    choices=["CPU Only", "CUDA GPU", "Metal GPU (Apple)"],
                    value=user_preferences.get("compute_device", "CPU Only"),
                    label="Compute Device",
                    info="CPU is most stable. Use GPU if available for higher throughput."
                )
                compute_type_dropdown = gr.Dropdown(
                    choices=["int8", "float16", "float32"],
                    value=user_preferences.get("compute_type", "int8"),
                    label="Compute Precision",
                    info="int8 = fastest/lowest memory, float32 = highest quality/most memory."
                )
            
            gr.Markdown(
                "**Device**: CPU = stable, GPU = faster (if available). **Precision**: int8 = fastest/least memory, float32 = highest quality/most memory."
            )
            
            # Auto-save status for compute settings
            compute_status = gr.Textbox(label="Compute Settings Status", lines=2, interactive=False)
            
            def autosave_compute_settings(device, compute_type, whisper_model_size):
                """Persist compute-related settings immediately without reloading the model to avoid disruptions."""
                try:
                    global user_preferences
                    user_preferences.update({
                        "compute_device": device,
                        "compute_type": compute_type,
                        "whisper_model_size": str(whisper_model_size),
                    })
                    save_user_preferences(user_preferences)
                    # Do NOT reload model here to keep current session uninterrupted.
                    # Model will pick these on next Apply All or next model init.
                    return f"Saved: device={device}, precision={compute_type}, model={whisper_model_size}"
                except Exception as e:
                    return f"Error saving compute settings: {e}"

            # Persist changes when any compute control changes
            device_dropdown.change(
                fn=autosave_compute_settings,
                inputs=[device_dropdown, compute_type_dropdown, whisper_model_dropdown],
                outputs=[compute_status]
            )
            compute_type_dropdown.change(
                fn=autosave_compute_settings,
                inputs=[device_dropdown, compute_type_dropdown, whisper_model_dropdown],
                outputs=[compute_status]
            )
            whisper_model_dropdown.change(
                fn=autosave_compute_settings,
                inputs=[device_dropdown, compute_type_dropdown, whisper_model_dropdown],
                outputs=[compute_status]
            )
            
            with gr.Row():
                preset_dropdown = gr.Dropdown(
                    choices=["Custom", "CPU Optimized", "Balanced", "Quality Focused"],
                    value="Custom",
                    label="Performance Preset",
                    info="Pre-baked settings. 'Custom' uses your sliders. Presets won't override your VAD checkbox."
                )
            
            gr.Markdown(
                "**Presets**: CPU Optimized = efficiency for slower hardware. Balanced = recommended. Quality Focused = best accuracy but higher resource usage."
            )
            
            gr.Markdown("---")
            gr.Markdown("## 💾 Apply & Save All Settings")
            
            # Single unified status display
            unified_status = gr.Textbox(label="Settings Status", lines=3, info="Status and messages from applying settings.")
            
            def apply_all_settings(block_ms, overlap_ms, min_sil_ms, min_speech_ms, max_speech_s, 
                                 no_speech_th, vad_enabled, cpu_threads, batch_size, buffer_duration, 
                                 energy_threshold, device, compute_type, whisper_model_size, preset_name):
                try:
                    messages = []
                    
                    # DEBUG: Log what we received from the UI
                    core.log_message(f"DEBUG: VAD checkbox value received: {vad_enabled} (type: {type(vad_enabled)})")
                    core.log_message(f"DEBUG: Preset selected: {preset_name}")
                    
                    # Apply preset if not Custom (but don't override VAD checkbox if user manually set it)
                    if preset_name != "Custom":
                        if preset_name == "CPU Optimized":
                            block_ms, overlap_ms = 50, 400
                            min_sil_ms, min_speech_ms, max_speech_s = 1000, 1800, 6.0
                            no_speech_th = 0.8
                            # Don't override vad_enabled - keep user's checkbox value
                        elif preset_name == "Balanced":
                            block_ms, overlap_ms = 30, 500
                            min_sil_ms, min_speech_ms, max_speech_s = 800, 1500, 8.0
                            no_speech_th = 0.7
                            # Don't override vad_enabled - keep user's checkbox value
                        elif preset_name == "Quality Focused":
                            block_ms, overlap_ms = 20, 600
                            min_sil_ms, min_speech_ms, max_speech_s = 600, 1000, 12.0
                            no_speech_th = 0.6
                            # Don't override vad_enabled - keep user's checkbox value
                        messages.append(f"Applied {preset_name} preset (VAD filter kept as user set)")
                    
                    # Apply timing parameters
                    RUNTIME_PARAMS.update({
                        "block_duration_ms": int(block_ms),
                        "overlap_s": float(overlap_ms) / 1000.0,
                        "min_silence_s": float(min_sil_ms) / 1000.0,
                        "min_speech_s": float(min_speech_ms) / 1000.0,
                        "max_speech_s": float(max_speech_s)
                    })
                    
                    # Apply Whisper model size
                    core.WHISPER_MODEL_SIZE = str(whisper_model_size)
                    
                    # Apply VAD settings - ensure they're properly set
                    core.NO_SPEECH_THRESHOLD = float(no_speech_th)
                    core.VAD_FILTER = bool(vad_enabled)
                    
                    # Log VAD settings for verification
                    core.log_message(f"VAD settings applied: NO_SPEECH_THRESHOLD={core.NO_SPEECH_THRESHOLD}, VAD_FILTER={core.VAD_FILTER}")
                    core.log_message(f"Requested Whisper model size: {core.WHISPER_MODEL_SIZE}")
                    
                    # Apply CPU settings
                    os.environ["OMP_NUM_THREADS"] = str(int(cpu_threads))
                    os.environ["MKL_NUM_THREADS"] = str(int(cpu_threads))
                    
                    # Update audio buffer if needed
                    global audio_buffer
                    if audio_buffer.max_size != int(core.TARGET_RATE * buffer_duration):
                        old_audio = audio_buffer.get_audio()
                        audio_buffer = CircularAudioBuffer(max_duration_seconds=buffer_duration)
                        if len(old_audio) > 0:
                            audio_buffer.add_audio(old_audio[-int(core.TARGET_RATE * 2):])
                    
                    # Update user preferences
                    global user_preferences
                    
                    # DEBUG: Log VAD filter before saving
                    core.log_message(f"DEBUG: About to save vad_filter as: {bool(vad_enabled)}")
                    
                    user_preferences.update({
                        "block_duration_ms": int(block_ms),
                        "overlap_ms": int(overlap_ms),
                        "min_silence_ms": int(min_sil_ms),
                        "min_speech_ms": int(min_speech_ms),
                        "max_speech_s": float(max_speech_s),
                        "no_speech_threshold": float(no_speech_th),
                        "vad_filter": bool(vad_enabled),
                        "cpu_threads": int(cpu_threads),
                        "processing_batch_size": int(batch_size),
                        "buffer_duration_s": int(buffer_duration),
                        "speech_energy_threshold": float(energy_threshold),
                        "compute_device": device,
                        "compute_type": compute_type,
                        "whisper_model_size": str(whisper_model_size)
                    })
                    
                    # DEBUG: Confirm what was saved
                    core.log_message(f"DEBUG: Saved vad_filter in user_preferences: {user_preferences.get('vad_filter')}")
                    
                    # Force Whisper model reload with new hardware/model settings
                    global whisper_model
                    whisper_model = None
                    try:
                        # Build a fresh model immediately so subsequent actions use it without delay
                        new_model = get_whisper_model()
                        actual_device = getattr(new_model.model, 'device', 'unknown')
                        core.log_message(f"Whisper model reloaded: size={core.WHISPER_MODEL_SIZE}, device={actual_device}, precision={user_preferences.get('compute_type')}")
                    except Exception as e:
                        core.log_message(f"Failed to eagerly reload Whisper model: {e}", "WARNING")
                    
                    # Save all preferences
                    save_user_preferences(user_preferences)
                    
                    messages.extend([
                        "✅ Timing settings applied",
                        f"✅ VAD settings applied: threshold={float(no_speech_th)}, filter={'ON' if bool(vad_enabled) else 'OFF'}",
                        "✅ CPU performance settings applied", 
                        f"✅ Whisper model will reload with {device} + {compute_type}",
                        "✅ All settings saved to preferences"
                    ])
                    
                    return "\n".join(messages)
                    
                except Exception as e:
                    return f"❌ Error applying settings: {e}"
            
            # Single unified apply button
            apply_all_btn = gr.Button("🚀 Apply & Save All Settings", variant="primary", size="lg")
            
            apply_all_btn.click(
                fn=apply_all_settings,
                inputs=[
                    s_block_ms, s_overlap_ms, s_min_silence_ms, s_min_speech_ms, s_max_speech_s,
                    s_no_speech, s_vad_filter, s_cpu_threads, s_processing_batch, s_buffer_size,
                    s_energy_threshold, device_dropdown, compute_type_dropdown, whisper_model_dropdown, preset_dropdown
                ],
                outputs=[unified_status]
            )

            
            gr.Markdown("---")
            gr.Markdown("## ⚡ Audio-Text Synchronization (Optional)")
            with gr.Row():
                s_text_delay = gr.Slider(
                    minimum=-2.0, maximum=5.0, step=0.1,
                    value=float(user_preferences.get("text_display_delay", 0.0)),
                    label="Text Display Delay (s)"
                )
                s_audio_delay = gr.Slider(
                    minimum=0.0, maximum=3.0, step=0.1,
                    value=float(user_preferences.get("audio_output_delay", 0.0)),
                    label="Audio Output Delay (s)"
                )
            
            def apply_sync_settings(text_delay, audio_delay):
                try:
                    global user_preferences
                    user_preferences.update({
                        "text_display_delay": float(text_delay),
                        "audio_output_delay": float(audio_delay)
                    })
                    save_user_preferences(user_preferences)
                    return f"Sync settings applied: Text delay {text_delay}s, Audio delay {audio_delay}s"
                except Exception as e:
                    return f"Error applying sync settings: {e}"
            
            sync_status = gr.Textbox(label="Sync Status")
            apply_sync_btn = gr.Button("Apply Sync Settings")
            apply_sync_btn.click(
                fn=apply_sync_settings,
                inputs=[s_text_delay, s_audio_delay],
                outputs=[sync_status]
            )

            
        gr.Markdown("## Translation History")
        with gr.Accordion("View Translation Logs", open=False):
            def get_logs():
                log_file = core.get_log_filename()
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8") as f:
                        return f.read()
                return "No logs found for today."
            
            logs_output = gr.Textbox(label="Today's Logs")
            refresh_logs = gr.Button("Refresh Logs")
            
            refresh_logs.click(
                fn=get_logs,
                inputs=[],
                outputs=[logs_output]
            )
    
    return app


# --- Main Function ---
if __name__ == "__main__":
    # Create and launch the Gradio interface
    app = create_ui()
    app.launch(server_name="0.0.0.0", share=False)
