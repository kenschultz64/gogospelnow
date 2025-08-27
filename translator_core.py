# SPDX-License-Identifier: Apache-2.0

import os
import numpy as np
import logging
import asyncio
import requests
import re
import time
import datetime
import json
import threading
from openai import OpenAI
from faster_whisper import WhisperModel

# --- Configuration ---
LOGS_DIR = "translation_logs"
SETTINGS_FILE = "settings.json"
# Default values, will be potentially overwritten by settings file
DEFAULT_SETTINGS = {
    "translation_server": "http://localhost:11434",
    "tts_server_url": "http://localhost:8880/v1",
}

# --- Runtime VAD/Whisper controls (can be updated by UI) ---
# Make these module-level so the app can adjust them without restarting
NO_SPEECH_THRESHOLD: float = 0.7  # higher = stricter silence detection
VAD_FILTER: bool = False          # Whisper's internal VAD (may drop soft speech on Linux)

WHISPER_MODEL_SIZE = "small"
# Map display names to Whisper language codes (ISO 639-1)
# None for Auto-Detect
LANGUAGE_CODES = {
    # Detection
    "Auto-Detect": None,

    # Europe
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Russian": "ru",
    "Ukrainian": "uk",
    "Polish": "pl",
    "Czech": "cs",
    "Slovak": "sk",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Bulgarian": "bg",
    "Serbian": "sr",
    "Croatian": "hr",
    "Slovenian": "sl",
    "Bosnian": "bs",
    "Albanian": "sq",
    "Greek": "el",
    "Turkish": "tr",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Icelandic": "is",
    "Lithuanian": "lt",
    "Latvian": "lv",
    "Estonian": "et",
    "Irish": "ga",
    "Welsh": "cy",
    "Catalan": "ca",
    "Galician": "gl",
    "Basque": "eu",

    # Middle East / Central Asia
    "Arabic": "ar",
    "Hebrew": "he",
    "Persian (Farsi)": "fa",
    "Pashto": "ps",
    "Kurdish": "ku",
    "Azerbaijani": "az",
    "Armenian": "hy",
    "Georgian": "ka",
    "Kazakh": "kk",
    "Uzbek": "uz",

    # South Asia
    "Hindi": "hi",
    "Urdu": "ur",
    "Bengali": "bn",
    "Punjabi": "pa",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Sinhala": "si",
    "Nepali": "ne",

    # East / Southeast Asia
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Vietnamese": "vi",
    "Thai": "th",
    "Lao": "lo",
    "Khmer": "km",
    "Burmese": "my",
    "Mongolian": "mn",
    "Indonesian": "id",
    "Malay": "ms",
    "Filipino (Tagalog)": "tl",

    # Africa
    "Swahili": "sw",
    "Amharic": "am",
    "Somali": "so",
    "Yoruba": "yo",
    "Hausa": "ha",
    "Zulu": "zu",
    "Afrikaans": "af",

    # Americas / Other
    "Haitian Creole": "ht",
}
# Create reverse mapping for convenience (code -> display name)
CODE_TO_LANGUAGE = {v: k for k, v in LANGUAGE_CODES.items() if v is not None}

SOURCE_LANGUAGES = list(LANGUAGE_CODES.keys())  # Use keys from mapping
TARGET_LANGUAGES = [
    "🇺🇸 American English",
    "🇬🇧 British English", 
    "🇪🇸 Spanish",
    "🇫🇷 French",
    "🇩🇪 German",
    "🇮🇹 Italian",
    "🇵🇹 Portuguese",
    "🇧🇷 Brazilian Portuguese",
    "🇳🇱 Dutch",
    "🇷🇺 Russian",
    "🇵🇱 Polish",
    "🇨🇿 Czech",
    "🇭🇺 Hungarian",
    "🇬🇷 Greek",
    "🇹🇷 Turkish",
    "🇸🇪 Swedish",
    "🇳🇴 Norwegian",
    "🇩🇰 Danish",
    "🇫🇮 Finnish",
    "🇯🇵 Japanese",
    "🇨🇳 Mandarin Chinese",
    "🇰🇷 Korean",
    "🇻🇳 Vietnamese",
    "🇹🇭 Thai",
    "🇮🇩 Indonesian",
    "🇮🇳 Hindi",
    "🇦🇪 Arabic",
    "🇮🇱 Hebrew",
    "🇮🇷 Persian (Farsi)",
    "🇭🇹 Haitian Creole",
    "🇿🇦 Afrikaans",
    "🇹🇿 Swahili",
]
KOKORO_VOICES = [  # Added Kokoro Voices List
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
    "ef_dora",
    "em_alex",
    "em_santa",
    "ff_siwis",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    "if_sara",
    "im_nicola",
    "pf_dora",
    "pm_alex",
    "pm_santa",
]
TARGET_RATE = 16000
BLOCK_DURATION_MS = 100

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def get_log_filename():
    now = datetime.datetime.now()
    return os.path.join(LOGS_DIR, f"translation_log_{now.strftime('%Y-%m-%d')}.txt")


# --- Core Functions ---
def log_message(message, level="INFO"):
    """Logs messages to console and file."""
    logger = logging.getLogger()
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "DEBUG":
        logger.debug(message)
    return message


def log_translation_file(english_text, translated_text, target_language):
    """Logs the translation to a file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = get_log_filename()
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}]\n")
            f.write(f"English: {english_text}\n")
            f.write(f"{target_language}: {translated_text}\n")
            f.write("-" * 50 + "\n")
        log_message(f"Translation logged to {os.path.basename(log_file)}")
    except Exception as e:
        log_message(f"Error writing to log file: {e}", "ERROR")


def load_settings():
    """Loads settings from SETTINGS_FILE or returns defaults."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                # Validate basic structure (can be expanded)
                if (
                    isinstance(loaded, dict)
                    and "translation_server" in loaded
                    and "tts_server_url" in loaded
                ):
                    log_message(f"Loaded settings from {SETTINGS_FILE}")
                    return loaded
                else:
                    log_message(
                        f"Invalid format in {SETTINGS_FILE}. Using defaults.", "WARNING"
                    )
        else:
            log_message(f"{SETTINGS_FILE} not found. Using defaults.")
    except (json.JSONDecodeError, IOError) as e:
        log_message(f"Error loading settings: {e}. Using defaults.", "ERROR")

    return DEFAULT_SETTINGS.copy()  # Ensure defaults are used if loading fails


def clean_language_name(language_name):
    """Remove flag emojis and extra descriptors from language names for translation prompts."""
    import re
    # Remove flag emojis (Unicode flag characters)
    cleaned = re.sub(r'[\U0001F1E6-\U0001F1FF]{2}\s*', '', language_name)
    # Handle specific cases
    if "American English" in cleaned:
        return "English"
    elif "British English" in cleaned:
        return "English"
    elif "Mandarin Chinese" in cleaned:
        return "Chinese"
    elif "Brazilian Portuguese" in cleaned:
        return "Portuguese"
    return cleaned.strip()

def translate(
    text, source_language, target_language, model_name, current_settings=None
):
    """Translates text using the Ollama server."""
    if current_settings is None:
        current_settings = load_settings()
        
    # Use current setting for server URL
    translation_server_url = current_settings.get(
        "translation_server", DEFAULT_SETTINGS["translation_server"]
    )
    
    # Clean language names for the translation prompt
    clean_source = clean_language_name(source_language)
    clean_target = clean_language_name(target_language)
    
    log_message(
        f"Translating from {source_language} to {target_language} using {model_name} via {translation_server_url}: '{text}'"
    )
    # Adjust prompt based on source language
    prompt_source_lang = (
        clean_source if source_language != "Auto-Detect" else "the detected language"
    )

    prompt = f"""
Translate the following text from {prompt_source_lang} to {clean_target}. Provide only the translation, without any explanations or extra text.

{prompt_source_lang}: {text}
{clean_target}:
"""
    try:
        payload = {
            "model": model_name,  # Use selected model
            "prompt": prompt,
            "stream": False,
            "keep_alive": "60m",
        }
        response = requests.post(
            f"{translation_server_url}/api/generate",
            json=payload,
            timeout=60,  # Use dynamic URL
        )
        response.raise_for_status()
        result = response.json()
        translation = result.get("response", "").strip()
        translation = translation.split("\n")[0]
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]
        if not translation:
            log_message("Translation result was empty.", "WARNING")
            return None
        log_message(f"Translation: {translation}")
        log_translation_file(text, translation, target_language)
        return translation
    except requests.exceptions.Timeout:
        log_message("Translation API request timed out.", "ERROR")
        return None
    except requests.exceptions.ConnectionError as e:
        log_message(f"Translation API connection error: {e}", "ERROR")
        return None
    except requests.exceptions.RequestException as e:
        log_message(f"Translation API request error: {e}", "ERROR")
        return None
    except Exception as e:
        log_message(f"Unexpected translation error: {e}", "ERROR")
        return None


def transcribe_audio(audio, source_language, whisper_model=None):
    """Transcribes audio using the Faster Whisper model."""
    # Mark transcribing active
    try:
        transcribing_event.set()
    except NameError:
        # If events not yet defined, ignore
        pass
    if whisper_model is None:
        log_message(f"Loading Whisper model ({WHISPER_MODEL_SIZE}) with CPU optimizations...")
        whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE, 
            device="cpu", 
            compute_type="int8",
            num_workers=1  # CPU optimization
        )
        log_message("Whisper model loaded.")
        
    try:
        if audio.dtype != np.float32:
            log_message(
                f"Incorrect audio dtype: {audio.dtype}, converting.", "WARNING"
            )
            audio = audio.astype(np.float32)
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            log_message(
                f"Audio max abs value {max_val:.3f} > 1.0, normalizing.", "DEBUG"
            )
            audio = audio / max_val
        elif max_val == 0:
            log_message("Audio segment is pure silence.", "DEBUG")
            return None, None

        energy = np.abs(audio).mean()
        if energy < 0.0001:
            log_message(f"Audio energy ({energy:.4f}) too low, skipping.", "DEBUG")
            return None, None

        log_message(
            f"Transcribing audio segment (shape: {audio.shape}, dtype: {audio.dtype}, energy: {energy:.4f})",
            "DEBUG",
        )
        # Determine language code for Whisper using the mapping
        whisper_lang_code = LANGUAGE_CODES.get(
            source_language, None
        )  # Get code from mapping

        segments, info = whisper_model.transcribe(
            audio,
            language=whisper_lang_code,  # Use the code (or None for auto-detect)
            temperature=0.0,
            no_speech_threshold=NO_SPEECH_THRESHOLD,
            vad_filter=VAD_FILTER,
            condition_on_previous_text=False,
            beam_size=1,              # CPU optimization: reduce beam size
            best_of=1,                # CPU optimization: reduce candidates
            word_timestamps=False     # CPU optimization: disable if not needed
        )
        # Get the actual language code detected or used
        detected_lang_code = info.language
        log_message(
            f"Detected/Used source language code: {detected_lang_code} (Confidence: {info.language_probability:.2f})"
        )

        text = " ".join([segment.text for segment in segments]).strip()
        # Allow single words - removed len(text.split()) < 2 check
        if not text:
            log_message(f"Filtered out empty transcription: '{text}'", "DEBUG")
            return None, None  # Return None for both text and lang_code
        log_message(f"Transcription: {text}")
        return text, detected_lang_code  # Return text and detected code
    except Exception as e:
        log_message(f"Transcription error: {e}", "ERROR")
        return None, None  # Return None for both text and lang_code
    finally:
        try:
            transcribing_event.clear()
        except NameError:
            pass


def is_complete_sentence(text):
    """Checks if text seems like a complete sentence (basic heuristic)."""
    if not text:
        return False
    if re.search(r"[.!?]$", text.strip()):
        return True
    if len(text.split()) >= 5:
        return True
    return False


def is_speech(audio_chunk, min_threshold=0.0008, max_threshold=0.6):
    """Checks if audio chunk energy is within speech range."""
    if audio_chunk is None or len(audio_chunk) == 0:
        return False
    energy = np.abs(audio_chunk).mean()
    # More lenient threshold to catch quieter speech
    return min_threshold < energy < max_threshold


async def text_to_speech_async(text, selected_voice, current_settings=None, output_device_idx=None):
    """Generates speech using OpenAI TTS with direct audio streaming."""
    if current_settings is None:
        current_settings = load_settings()
        
    tts_url = current_settings.get("tts_server_url", DEFAULT_SETTINGS["tts_server_url"])
    log_message(f"Attempting to initialize TTS client for URL: {tts_url}")
    
    try:
        speech_client = OpenAI(base_url=tts_url, api_key="not-needed")
        log_message(f"TTS client object created for {tts_url}.")
    except Exception as client_init_e:
        log_message(f"Failed to create OpenAI client for TTS: {client_init_e}", "ERROR")
        return None

    log_message(f"Generating speech with voice '{selected_voice}' for: '{text}'")
    
    try:
        # Stream audio data directly without creating files
        with speech_client.audio.speech.with_streaming_response.create(
            model="kokoro",
            voice=selected_voice,
            response_format="mp3",
            input=text,
            speed=1.0,
        ) as response:
            # Collect audio data in memory
            audio_data = b""
            for chunk in response.iter_bytes():
                audio_data += chunk
        
        log_message("Speech generated successfully")
        
        # If output device is specified, play the audio directly
        if output_device_idx is not None:
            try:
                import pyaudio
                import io
                from pydub import AudioSegment
                
                log_message(f"Playing audio through device {output_device_idx}")
                
                # Convert MP3 data to playable format
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
                
                # Convert to raw audio data
                raw_data = audio_segment.raw_data
                sample_rate = audio_segment.frame_rate
                channels = audio_segment.channels
                sample_width = audio_segment.sample_width
                
                # Initialize PyAudio
                p = pyaudio.PyAudio()
                
                try:
                    # Open stream
                    stream = p.open(
                        format=p.get_format_from_width(sample_width),
                        channels=channels,
                        rate=sample_rate,
                        output=True,
                        output_device_index=output_device_idx
                    )
                    
                    # Play audio
                    stream.write(raw_data)
                    stream.stop_stream()
                    stream.close()
                    
                    log_message(f"Audio played through device {output_device_idx}")
                finally:
                    p.terminate()
                    
            except Exception as play_error:
                log_message(f"Error playing audio through device {output_device_idx}: {play_error}", "ERROR")
                log_message("Audio playback failed")
        
        # Return None since we're not creating files anymore
        return None
        
    except (requests.exceptions.ConnectionError) as e:
        log_message(f"TTS API connection error: {e}", "ERROR")
        return None
    except Exception as e:
        log_message(f"Text-to-speech error: {e}", "ERROR")
        return None


def fetch_ollama_models(server_url=None):
    """Fetches available models from the Ollama API."""
    current_settings = load_settings()
    # Use provided URL or get from current settings
    translation_server_url = server_url or current_settings.get(
        "translation_server", DEFAULT_SETTINGS["translation_server"]
    )
    log_message(f"Fetching Ollama models from: {translation_server_url}")
    try:
        response = requests.get(f"{translation_server_url}/api/tags", timeout=5)
        response.raise_for_status()
        models_data = response.json()
        model_names = sorted([model["name"] for model in models_data.get("models", [])])
        if not model_names:
            log_message("No Ollama models found via API.", "WARNING")
            return ["llama3.2:3b-instruct-q4_K_M"]  # Return default if none found
        log_message(f"Found Ollama models: {', '.join(model_names)}")
        return model_names
    except requests.exceptions.ConnectionError:
        log_message(
            f"Could not connect to Ollama server at {translation_server_url} to fetch models.",
            "ERROR",
        )
        return ["llama3.2:3b-instruct-q4_K_M"]  # Return default on connection error
    except Exception as e:
        log_message(f"Error fetching Ollama models: {e}", "ERROR")
        return ["llama3.2:3b-instruct-q4_K_M"]  # Return default on other errors


# --- Health / Status Flags ---
# Events are thread-safe primitives to reflect state without heavy locking
services_ok_event = threading.Event()
transcribing_event = threading.Event()

# Cached health state to avoid frequent network calls
_last_health_check_ts = 0.0
_last_ollama_ok = False
_last_tts_ok = False
_ollama_fail_count = 0
_tts_fail_count = 0
_FAIL_THRESHOLD = 2  # require N consecutive fails to mark as down


def check_services_health(force=False, current_settings=None):
    """Lightweight health check for translation and TTS services with debounce.

    Returns a tuple (ollama_ok, tts_ok).
    """
    global _last_health_check_ts, _last_ollama_ok, _last_tts_ok, _ollama_fail_count, _tts_fail_count
    now = time.time()

    # Debounce to every ~2 seconds unless forced
    if not force and (now - _last_health_check_ts) < 2.0:
        return _last_ollama_ok, _last_tts_ok

    if current_settings is None:
        current_settings = load_settings()

    # Start with previous state; only flip to False after thresholded failures
    ollama_ok = _last_ollama_ok
    tts_ok = _last_tts_ok

    # Check Ollama
    try:
        translation_server_url = current_settings.get(
            "translation_server", DEFAULT_SETTINGS["translation_server"]
        )
        r = requests.get(f"{translation_server_url}/api/tags", timeout=0.8)
        r.raise_for_status()
        ollama_ok = True
        _ollama_fail_count = 0
    except requests.Timeout:
        # Inconclusive: keep previous state, do not increment fail count
        log_message("Health: Ollama check timeout (ignored)", "DEBUG")
    except Exception as e:
        _ollama_fail_count += 1
        log_message(f"Health: Ollama check failed ({_ollama_fail_count}): {e}", "WARNING")
        if _ollama_fail_count >= _FAIL_THRESHOLD:
            ollama_ok = False

    # Check TTS (OpenAI-compatible). Try a minimal GET to /models if supported.
    try:
        tts_url = current_settings.get("tts_server_url", DEFAULT_SETTINGS["tts_server_url"])
        # Some servers may not implement /models; still attempt as a quick ping.
        r2 = requests.get(f"{tts_url}/models", timeout=0.8)
        if r2.status_code < 500:
            tts_ok = True
            _tts_fail_count = 0
        else:
            _tts_fail_count += 1
            if _tts_fail_count >= _FAIL_THRESHOLD:
                tts_ok = False
    except requests.Timeout:
        # Inconclusive: keep previous state, do not increment fail count
        log_message("Health: TTS check timeout (ignored)", "DEBUG")
    except Exception as e:
        _tts_fail_count += 1
        log_message(f"Health: TTS check failed ({_tts_fail_count}): {e}", "WARNING")
        if _tts_fail_count >= _FAIL_THRESHOLD:
            tts_ok = False

    _last_health_check_ts = now
    _last_ollama_ok = ollama_ok
    _last_tts_ok = tts_ok

    if ollama_ok and tts_ok:
        services_ok_event.set()
    else:
        services_ok_event.clear()

    return ollama_ok, tts_ok


def get_status():
    """Return a dict summarizing backend service status and activity.

    Keys:
      - ollama_ok
      - tts_ok
      - services_ok
      - transcribing
      - detail (human-readable)
    """
    ollama_ok, tts_ok = check_services_health(force=False)
    transcribing = transcribing_event.is_set()
    services_ok = services_ok_event.is_set()

    issues = []
    if not ollama_ok:
        issues.append("Ollama unreachable")
    if not tts_ok:
        issues.append("TTS unreachable")
    detail = "; ".join(issues) if issues else ("Idle" if not transcribing else "Transcribing…")

    return {
        "ollama_ok": ollama_ok,
        "tts_ok": tts_ok,
        "services_ok": services_ok,
        "transcribing": transcribing,
        "detail": detail,
    }
