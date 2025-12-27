# SPDX-License-Identifier: Apache-2.0

import os
import sys
import subprocess
import re
import numpy as np
import sounddevice as sd
import queue
import threading
import multiprocessing as mp
import asyncio
import time
import json
import glob
from concurrent.futures import ThreadPoolExecutor
import gradio as gr
from fastapi import FastAPI
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel
from scipy.signal import resample
import threadpoolctl
try:
    from screeninfo import get_monitors
except ImportError:
    get_monitors = None

try:
    import tkinter as tk
except Exception:
    tk = None

# Import core functionality
import translator_core as core

# --- Global Variables & Queues ---
audio_queue = queue.Queue()
stop_event = threading.Event()
recording_thread = None
whisper_model = None
current_settings = core.load_settings()
recording_should_run = False
recording_params = None
translation_display_manager = None

# CPU optimization: Set thread limits
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"


def get_pref_value(key, default, *, min_value=None, max_value=None, cast_type=None):
    """Fetch a user preference with optional clamping/casting to keep UI controls valid."""
    value = None
    if isinstance(user_preferences, dict):
        value = user_preferences.get(key, default)
    if value is None:
        value = default
    target_type = cast_type or type(default)
    try:
        value = target_type(value)
    except Exception:
        value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value

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

# --- Translation Display Defaults ---
DISPLAY_FONT_CHOICES = [
    "Helvetica",
    "Arial",
    "Georgia",
    "Times New Roman",
    "Courier New",
    "Verdana",
    "Trebuchet MS",
    "Impact",
]

ALIGN_HORIZONTAL_CHOICES = ["Left", "Center", "Right"]
ALIGN_VERTICAL_CHOICES = ["Top", "Middle", "Bottom"]
H_ALIGN_TO_JUSTIFY = {
    "Left": "left",
    "Center": "center",
    "Right": "right",
}
H_ALIGN_TO_ANCHOR = {
    "Left": "w",
    "Center": "",
    "Right": "e",
}
V_ALIGN_TO_ANCHOR = {
    "Top": "n",
    "Middle": "",
    "Bottom": "s",
}

DEFAULT_TRANSLATION_DISPLAY_PREFS = {
    "display_font_family": DISPLAY_FONT_CHOICES[0],
    "display_font_size": 72,
    "display_font_color": "#FFFFFF",
    "display_bg_color": "#000000",
    "display_window_x": 0,
    "display_window_y": 0,
    "display_window_width": 1280,
    "display_window_height": 720,
    "display_always_on_top": True,
    "display_history_size": 1,
    "display_horizontal_align": "Center",
    "display_vertical_align": "Middle",
    "display_hold_seconds": 1.0,
    "display_monitor": 0,
}

# --- Runtime timing params (tunable via Settings UI) ---
# CPU-optimized defaults for better performance
RUNTIME_PARAMS = {
    "block_duration_ms": 30,   # Smaller blocks reduce perceived latency
    "min_silence_s": 0.6,      # Quicker silence detection to flush buffer sooner
    "min_speech_s": 1.2,       # Slightly shorter speech requirement for faster turns
    "max_speech_s": 8.0,       # Keep overall buffer size capped
    "overlap_s": 0.4           # Maintain tail audio to avoid clipping words
}

DEFAULT_TRANSLATION_WORKERS = 4

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
available_ollama_models = core.fetch_available_models(current_settings=current_settings)
input_devices = []
output_devices = []
selected_output_device_name = None
latest_translation_text = ""

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


def get_translation_display_config():
    """Return sanitized translation display preferences."""
    def _normalize_color_value(value, default_hex):
        if not value:
            return default_hex
        value = str(value).strip()
        if value.startswith("#"):
            hex_digits = value.lstrip("#")
            if len(hex_digits) == 3:
                hex_digits = "".join(ch * 2 for ch in hex_digits)
            if len(hex_digits) == 6 and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                return f"#{hex_digits.lower()}"
            return default_hex
        match = re.match(r"rgba?\(([^)]+)\)", value)
        if match:
            parts = [p.strip() for p in match.group(1).split(",")]
            def _channel(token):
                if token.endswith("%"):
                    try:
                        return max(0, min(255, round(float(token[:-1]) * 2.55)))
                    except ValueError:
                        return None
                try:
                    val = float(token)
                except ValueError:
                    return None
                if val <= 1.0:
                    val *= 255
                return max(0, min(255, round(val)))
            if len(parts) >= 3:
                channels = [_channel(parts[i]) for i in range(3)]
                if all(c is not None for c in channels):
                    return "#" + "".join(f"{c:02x}" for c in channels)
        return default_hex

    def _coerce_int(value, default):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _coerce_float(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    config = DEFAULT_TRANSLATION_DISPLAY_PREFS.copy()
    if isinstance(user_preferences, dict):
        for key in DEFAULT_TRANSLATION_DISPLAY_PREFS:
            config[key] = user_preferences.get(key, DEFAULT_TRANSLATION_DISPLAY_PREFS[key])

    config["display_font_family"] = (
        config["display_font_family"] if config["display_font_family"] in DISPLAY_FONT_CHOICES else DISPLAY_FONT_CHOICES[0]
    )
    config["display_font_size"] = max(16, min(200, _coerce_int(config["display_font_size"], 72)))
    config["display_window_width"] = max(400, min(3840, _coerce_int(config["display_window_width"], 1280)))
    config["display_window_height"] = max(200, min(2160, _coerce_int(config["display_window_height"], 720)))
    config["display_window_x"] = _coerce_int(config["display_window_x"], 0)
    config["display_window_y"] = _coerce_int(config["display_window_y"], 0)
    config["display_manual_offset_x"] = _coerce_int(config.get("display_manual_offset_x"), 0)
    config["display_manual_offset_y"] = _coerce_int(config.get("display_manual_offset_y"), 0)
    config["display_font_color"] = _normalize_color_value(config.get("display_font_color", "#FFFFFF"), "#ffffff")
    config["display_bg_color"] = _normalize_color_value(config.get("display_bg_color", "#000000"), "#000000")
    config["display_always_on_top"] = bool(config.get("display_always_on_top", True))
    config["display_history_size"] = max(1, min(6, _coerce_int(config.get("display_history_size"), 1)))
    h_align = config.get("display_horizontal_align", "Center")
    v_align = config.get("display_vertical_align", "Middle")
    config["display_horizontal_align"] = h_align if h_align in ALIGN_HORIZONTAL_CHOICES else "Center"
    config["display_vertical_align"] = v_align if v_align in ALIGN_VERTICAL_CHOICES else "Middle"
    config["display_hold_seconds"] = max(0.0, min(10.0, _coerce_float(config.get("display_hold_seconds"), 1.0)))
    config["display_monitor"] = max(0, min(10, _coerce_int(config.get("display_monitor"), 0)))
    return config


class TranslationDisplayManager:
    """Manage a dedicated process running a tkinter window for translations."""

    def __init__(self):
        self._process = None
        self._queue = None
        self._lock = threading.Lock()
        self._latest_text = ""
        self._config = get_translation_display_config()

    def is_running(self):
        self._cleanup_dead_process()
        return self._process is not None and self._process.is_alive()

    def _cleanup_dead_process(self):
        if self._process is not None and not self._process.is_alive():
            try:
                self._process.join(timeout=0.2)
            except Exception:
                pass
            self._process = None
            self._queue = None

    def launch(self, config=None):
        # Helper to log to display_debug.txt from main process
        def log_main(msg):
            try:
                with open("display_debug.txt", "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - [MAIN] {msg}\n")
            except Exception:
                pass
        
        if tk is None:
            return False, "tkinter is not available on this system."
        with self._lock:
            self._cleanup_dead_process()
            if config:
                self._config = config.copy()
            
            log_main(f"Launch called. display_monitor={self._config.get('display_monitor')}, get_monitors available={get_monitors is not None}")
            
            # Resolve monitor coordinates in main process before spawning subprocess
            monitor_name = "primary monitor"
            if get_monitors:
                try:
                    monitors = get_monitors()
                    log_main(f"screeninfo returned {len(monitors)} monitors")
                    # Pass ALL monitor info to subprocess so 'm' key cycling works
                    all_monitors = []
                    for i, m in enumerate(monitors):
                        all_monitors.append({
                            "x": m.x, "y": m.y, 
                            "width": m.width, "height": m.height,
                            "is_primary": m.is_primary
                        })
                        log_main(f"  Monitor {i}: X={m.x}, Y={m.y}, {m.width}x{m.height}, primary={m.is_primary}")
                    self._config["all_monitors"] = all_monitors
                    
                    idx = int(self._config.get("display_monitor", 0))
                    log_main(f"Selected index: {idx}")
                    if 0 <= idx < len(monitors):
                        m = monitors[idx]
                        self._config["monitor_x"] = m.x
                        self._config["monitor_y"] = m.y
                        self._config["monitor_width"] = m.width
                        self._config["monitor_height"] = m.height
                        log_main(f"Set config: monitor_x={m.x}, monitor_y={m.y}, monitor_width={m.width}, monitor_height={m.height}")
                        # Calculate display number based on sorted X position (left to right)
                        # to match the dropdown display order
                        sorted_indices = sorted(range(len(monitors)), key=lambda i: monitors[i].x)
                        display_num = sorted_indices.index(idx) + 1  # 1-based
                        if m.is_primary:
                            monitor_name = f"Monitor {display_num} (PRIMARY)"
                        else:
                            monitor_name = f"Monitor {display_num}"
                    else:
                        log_main(f"Monitor index {idx} out of range (have {len(monitors)} monitors)")
                except Exception as e:
                    log_main(f"Monitor resolution failed: {e}")
                    import traceback
                    log_main(f"Traceback: {traceback.format_exc()}")
            else:
                log_main("screeninfo.get_monitors NOT available in main process!")
            
            log_main(f"Final config keys: {list(self._config.keys())}")
            
            if self.is_running():
                self._queue.put(("config", self._config))
                self._queue.put(("text", self._latest_text))
                return True, "Translation display already running – updated its settings."

            self._queue = mp.Queue()
            self._process = mp.Process(
                target=translation_display_process_main,
                args=(self._queue, self._config.copy(), self._latest_text),
                daemon=True,
            )
            self._process.start()
            if self._process.is_alive():
                return True, f"Launching translation display on {monitor_name}... (may take a few seconds)"
            self._queue = None
            self._process = None
            return False, "Failed to launch display."

    def close(self):
        with self._lock:
            self._cleanup_dead_process()
            if not self.is_running():
                return True, "Translation display is not running."
            if self._queue:
                self._queue.put(("close", None))
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.terminate()
            self._process = None
            self._queue = None
            return True, "Closing translation display."

    def update_text(self, text):
        self._latest_text = text or ""
        if self.is_running() and self._queue:
            self._queue.put(("text", self._latest_text))

    def apply_config(self, config):
        self._config = config.copy()
        if self.is_running() and self._queue:
            self._queue.put(("config", self._config))


def translation_display_process_main(cmd_queue, initial_config, initial_text):
    # Enable DPI awareness on Windows to fix coordinate issues
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    try:
        import tkinter as tk_process
    except Exception as exc:
        print(f"Translation display cannot start (tkinter error): {exc}")
        return
    
    # Import screeninfo locally in subprocess (global import doesn't carry over on Windows)
    try:
        from screeninfo import get_monitors as subprocess_get_monitors
    except ImportError:
        subprocess_get_monitors = None
    
    # Debug logging helper
    def log_debug(msg):
        try:
            with open("display_debug.txt", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception:
            pass
            
    log_debug("--- Display Process Started ---")
    log_debug(f"Subprocess screeninfo available: {subprocess_get_monitors is not None}")

    root = tk_process.Tk()
    root.title("Translation Display")

    state = {
        "config": initial_config.copy(),
        "history": [],
        "last_update_time": None,
        "pending_clear": False,
        "current_monitor_idx": int(initial_config.get("display_monitor", 0))
    }
    
    log_debug(f"Initial config: {state['config']}")

    if initial_text:
        state["history"].append(initial_text)
        state["last_update_time"] = None

    def compute_alignment(cfg):
        h = cfg.get("display_horizontal_align", "Center")
        v = cfg.get("display_vertical_align", "Middle")
        anchor = f"{V_ALIGN_TO_ANCHOR.get(v, '')}{H_ALIGN_TO_ANCHOR.get(h, '')}"
        justify = H_ALIGN_TO_JUSTIFY.get(h, "center")
        return (anchor or "center", justify)

    anchor, justify = compute_alignment(state["config"])

    # Check for initial transparency
    initial_bg = state["config"]["display_bg_color"]
    if isinstance(initial_bg, str) and len(initial_bg) == 9 and initial_bg.startswith("#") and initial_bg.endswith("00"):
        # Transparent background requested
        if sys.platform == "darwin":
            initial_bg = 'systemTransparent'
            root.attributes("-transparent", True)
            root.config(bg='systemTransparent')
        else:
            initial_bg = initial_bg[:7]  # Use RGB part only

    label = tk_process.Label(
        root,
        text="",
        fg=state["config"]["display_font_color"],
        bg=initial_bg,
        font=(state["config"]["display_font_family"], state["config"]["display_font_size"]),
        wraplength=max(100, state["config"]["display_window_width"] - 60),
        justify=justify,
        anchor=anchor,
    )
    label.pack(fill="both", expand=True, padx=20, pady=20)

    def activate_app_on_mac():
        if sys.platform != "darwin":
            return
        applescript = (
            'tell application "System Events" to set frontmost of process "Python" to true'
        )
        try:
            subprocess.run(["/usr/bin/osascript", "-e", applescript], check=False)
        except Exception:
            pass

    def bring_to_front():
        try:
            root.deiconify()
            root.lift()
            root.focus_force()
        except Exception:
            pass
        activate_app_on_mac()

    def apply_config(cfg):
        monitor_index = int(cfg.get("display_monitor", 0))
        state["current_monitor_idx"] = monitor_index
        
        # Base Auto-detected Offsets
        auto_x = 0
        auto_y = 0
        
        # Check if Main Process resolved coordinates
        if "monitor_x" in cfg and "monitor_y" in cfg:
             auto_x = int(cfg["monitor_x"])
             auto_y = int(cfg["monitor_y"])
             log_debug(f"Auto-detect (Main Process): X={auto_x}, Y={auto_y}")
        else:
             # Fallback to local detection using subprocess-local import
             try:
                if subprocess_get_monitors:
                    monitors = subprocess_get_monitors()
                    if 0 <= monitor_index < len(monitors):
                        auto_x = monitors[monitor_index].x
                        auto_y = monitors[monitor_index].y
                        log_debug(f"Auto-detect (Subprocess): X={auto_x}, Y={auto_y}")
                else:
                    log_debug("Subprocess fallback: screeninfo not available")
             except Exception as e:
                log_debug(f"Subprocess fallback failed: {e}")

        # Manual Offsets (Additive)
        manual_x = int(cfg.get("display_manual_offset_x", 0))
        manual_y = int(cfg.get("display_manual_offset_y", 0))
        log_debug(f"Manual Offsets: X={manual_x}, Y={manual_y}")

        # Final Calculation
        x_offset = auto_x + manual_x
        y_offset = auto_y + manual_y
        
        # Use user-configured dimensions (Window Width/Height sliders)
        # This allows custom sizes like 1280x720 on a 1080p monitor
        w = cfg.get('display_window_width', 1920)
        h = cfg.get('display_window_height', 1080)
        log_debug(f"Using configured dimensions: {w}x{h}")
        
        final_x = x_offset + cfg['display_window_x']
        final_y = y_offset + cfg['display_window_y']
        
        log_debug(f"FINAL COORDINATES: X={final_x}, Y={final_y}, Size={w}x{h}")
        
        geometry = f"{w}x{h}+{final_x}+{final_y}"
        log_debug(f"Applying Geometry: {geometry}")

        # 1. Standard Tkinter Geometry
        root.overrideredirect(False) # Turn off to set position
        root.geometry(geometry)
        root.update()
        root.overrideredirect(True)  # Turn back on
        
        # 2. Windows API Force Positioning (The "Nuclear Option")
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # SWP_NOSIZE=1, SWP_NOZORDER=4, SWP_SHOWWINDOW=0x0040
                hwnd = user32.GetParent(root.winfo_id())
                if hwnd == 0:
                    hwnd = root.winfo_id()
                
                log_debug(f"Calling SetWindowPos on HWND {hwnd} -> {final_x}, {final_y}")
                
                # SetWindowPos(hwnd, hWndInsertAfter, x, y, cx, cy, uFlags)
                # HWND_TOP = 0
                user32.SetWindowPos(hwnd, 0, int(final_x), int(final_y), int(w), int(h), 0x0040)
            except Exception as e:
                log_debug(f"Windows API positioning failed: {e}")

        # 3. Delayed Re-application
        def force_geometry():
            root.geometry(geometry)
            root.lift()
            # Try Windows API again after delay
            if sys.platform == "win32":
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
                    user32.SetWindowPos(hwnd, 0, int(final_x), int(final_y), int(w), int(h), 0x0040)
                except Exception:
                    pass
        root.after(200, force_geometry)
        
        # Handle transparency
        bg_color = cfg["display_bg_color"]
        is_transparent = False
        if isinstance(bg_color, str) and len(bg_color) == 9 and bg_color.startswith("#") and bg_color.endswith("00"):
            is_transparent = True
            bg_color_rgb = bg_color[:7]
        else:
            bg_color_rgb = bg_color
            
        root.configure(bg=bg_color_rgb)
        
        try:
            root.attributes("-topmost", bool(cfg.get("display_always_on_top", True)))
            if is_transparent and sys.platform == "win32":
                 root.attributes("-transparentcolor", bg_color_rgb)
        except Exception as e:
            log_debug(f"Error setting attributes: {e}")
        
        anchor, justify = compute_alignment(cfg)
        label.configure(
            fg=cfg["display_font_color"],
            bg=bg_color_rgb, 
            font=(cfg["display_font_family"], cfg["display_font_size"]),
            wraplength=max(100, cfg["display_window_width"] - 60),
            justify=justify,
            anchor=anchor,
        )

        max_items = max(1, int(cfg.get("display_history_size", 1)))
        state["history"] = state["history"][-max_items:]
        render_history()
        bring_to_front()

    # Capture click to focus window (Fix for 'm' key not working)
    def on_click(event):
        root.focus_force()
    root.bind("<Button-1>", on_click)

    # Add right-click menu to close the window
    context_menu = tk_process.Menu(root, tearoff=0)
    context_menu.add_command(label="Close Display", command=lambda: cmd_queue.put(("close", None)))
    
    def show_context_menu(event):
        try:
            context_menu.tk_popup(event.x_root, event.y_popup)
        finally:
            context_menu.grab_release()

    root.bind("<Button-3>", show_context_menu)
    if sys.platform == "darwin":
        root.bind("<Button-2>", show_context_menu)

    # Allow closing with Escape key
    root.bind("<Escape>", lambda e: cmd_queue.put(("close", None)))
    
    # Manual Monitor Cycle Binding ('m') - Uses pre-passed monitor data from main process
    def cycle_monitor(event):
        try:
            all_monitors = state["config"].get("all_monitors", [])
            num_monitors = len(all_monitors)
            if num_monitors > 1:
                state["current_monitor_idx"] = (state["current_monitor_idx"] + 1) % num_monitors
                state["config"]["display_monitor"] = state["current_monitor_idx"]
                # Update monitor coordinates and dimensions for the new monitor
                m = all_monitors[state["current_monitor_idx"]]
                state["config"]["monitor_x"] = m["x"]
                state["config"]["monitor_y"] = m["y"]
                state["config"]["monitor_width"] = m["width"]
                state["config"]["monitor_height"] = m["height"]
                log_debug(f"Manual cycle to monitor {state['current_monitor_idx']}: X={m['x']}, Y={m['y']}, Size={m['width']}x{m['height']}")
                apply_config(state["config"])
            else:
                log_debug(f"Cannot cycle monitors: only {num_monitors} monitor(s) available in passed data")
        except Exception as e:
            log_debug(f"Error cycling monitors: {e}")

    root.bind("<m>", cycle_monitor)
    root.bind("<M>", cycle_monitor)

    # Add a subtle floating Close button (X) in top-right - hidden by default, appears on hover
    # Also bind Escape key to close for keyboard control during worship
    def close_display():
        cmd_queue.put(("close", None))
    
    root.bind("<Escape>", lambda e: close_display())
    
    # Create a subtle close button that's nearly invisible until hovered
    close_btn = tk_process.Label(
        root, 
        text="×", 
        bg=state["config"].get("display_bg_color", "#000000"),  # Match background
        fg="#666666",  # Very dim gray
        bd=0, 
        padx=8,
        pady=4,
        font=("Arial", 14),
        cursor="hand2"
    )
    close_btn.place(relx=1.0, x=-5, y=5, anchor="ne")
    
    # Make it more visible on hover
    def on_hover(event):
        close_btn.configure(fg="#ffffff", bg="#333333")
    def on_leave(event):
        close_btn.configure(fg="#666666", bg=state["config"].get("display_bg_color", "#000000"))
    def on_click(event):
        close_display()
    
    close_btn.bind("<Enter>", on_hover)
    close_btn.bind("<Leave>", on_leave)
    close_btn.bind("<Button-1>", on_click)

    def render_history():
        if state["history"]:
            label.configure(text="\n\n".join(state["history"]))
        else:
            label.configure(text="")

    apply_config(state["config"])
    root.after(150, bring_to_front)
    render_history()

    def handle_close_from_window():
        cmd_queue.put(("close", None))

    root.protocol("WM_DELETE_WINDOW", handle_close_from_window)

    def on_window_configure(event):
        """Handle window resize/maximize events to update text wrapping dynamically."""
        if event.widget == root:
            new_width = event.width
            new_height = event.height
            # Update wraplength based on actual window width to fix transcript display on resize/maximize
            label.configure(wraplength=max(100, new_width - 60))
            # Store the new dimensions in config for persistence
            state["config"]["display_window_width"] = new_width
            state["config"]["display_window_height"] = new_height

    # Bind the configure event to handle window resize/maximize
    root.bind("<Configure>", on_window_configure)

    def poll_queue():
        import time
        try:
            while True:
                item_type, payload = cmd_queue.get_nowait()
                if item_type == "text":
                    if payload:
                        # Update timestamp when new text arrives
                        state["last_update_time"] = time.time()
                        state["history"].append(payload)
                        max_items = max(1, int(state["config"].get("display_history_size", 1)))
                        state["history"] = state["history"][-max_items:]
                        render_history()
                elif item_type == "config":
                    state["config"] = payload.copy()
                    apply_config(state["config"])
                elif item_type == "close":
                    root.destroy()
                    return
        except queue.Empty:
            pass
        except (EOFError, OSError):
            return
        
        # Check if we should clear old text based on hold_seconds setting
        # This runs independently of the transcription pipeline
        hold_seconds = float(state["config"].get("display_hold_seconds", 1.0))
        max_items = max(1, int(state["config"].get("display_history_size", 1)))
        
        # Enforce history size limit - remove excess items immediately
        # When new text arrives, it automatically replaces old text via [-max_items:] slicing
        if len(state["history"]) > max_items:
            state["history"] = state["history"][-max_items:]
            render_history()
        
        # Auto-clear old text after hold time expires (only for multi-line displays)
        # For single line (max_items=1), new text replaces old text immediately on arrival
        if max_items > 1 and state["last_update_time"] is not None and len(state["history"]) > 1:
            elapsed = time.time() - state["last_update_time"]
            # Only clear if hold time has elapsed and we have multiple items
            if elapsed > hold_seconds:
                # Clear the oldest item to make room for new ones
                state["history"].pop(0)
                render_history()
                state["last_update_time"] = time.time()  # Reset timer for next item
        
        root.after(100, poll_queue)

    poll_queue()
    try:
        root.mainloop()
    except Exception as exc:
        print(f"Translation display crashed: {exc}")


def ensure_translation_display_manager():
    global translation_display_manager
    if translation_display_manager is None:
        translation_display_manager = TranslationDisplayManager()
    return translation_display_manager


def broadcast_translation_to_display(text):
    global latest_translation_text
    if not text:
        return
    if text == latest_translation_text:
        return
    latest_translation_text = text
    if translation_display_manager and translation_display_manager.is_running():
        # Send full text to preserve accuracy - display will handle truncation if needed
        translation_display_manager.update_text(text)

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

def reload_whisper_model(force=False):
    """Force Whisper model to reload e.g. after compute setting changes."""
    global whisper_model
    if force and whisper_model is not None:
        try:
            del whisper_model
        except Exception:
            pass
    whisper_model = None
    return get_whisper_model()

def restart_recording_if_needed(was_recording):
    """Restart continuous recording if it was active before a reload."""
    if not was_recording:
        return
    if recording_should_run and recording_params:
        core.log_message("Restarting recording after compute reload", "INFO")
        try:
            start_continuous_recording(*recording_params)
        except Exception as e:
            core.log_message(f"Failed to restart recording: {e}", "ERROR")

def is_recording_active():
    return recording_thread is not None and recording_thread.is_alive()

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
translation_executor = None
translation_results_queue = queue.Queue()
transcription_sequence = 0
last_displayed_transcription_id = 0

def get_translation_worker_count():
    pref_value = user_preferences.get("translation_workers") if isinstance(user_preferences, dict) else None
    try:
        return max(1, min(8, int(pref_value))) if pref_value else DEFAULT_TRANSLATION_WORKERS
    except Exception:
        return DEFAULT_TRANSLATION_WORKERS

def get_translation_executor():
    """Lazy-init thread pool dedicated to translation requests."""
    global translation_executor
    if translation_executor is None:
        translation_executor = ThreadPoolExecutor(
            max_workers=get_translation_worker_count(),
            thread_name_prefix="translation-worker"
        )
    return translation_executor

def refresh_translation_executor(new_worker_count=None):
    """Recreate translation executor if worker count changes."""
    global translation_executor
    if translation_executor is not None:
        translation_executor.shutdown(wait=False, cancel_futures=True)
        translation_executor = None
    if new_worker_count:
        user_preferences["translation_workers"] = new_worker_count
    return get_translation_executor()

def next_transcription_id():
    """Generate a monotonically increasing transcription identifier."""
    global transcription_sequence
    transcription_sequence += 1
    return transcription_sequence

def schedule_translation_task(transcription_id, transcription, source_lang_name, target_language, ollama_model, voice, output_device_idx):
    """Run translation in background and enqueue TTS/results when ready."""
    executor = get_translation_executor()
    settings_snapshot = dict(current_settings) if isinstance(current_settings, dict) else {}

    future = executor.submit(
        core.translate,
        transcription,
        source_lang_name,
        target_language,
        ollama_model,
        settings_snapshot
    )

    def _on_complete(fut):
        translation = None
        try:
            translation = fut.result()
        except Exception as e:
            core.log_message(f"Translation worker error: {e}", "ERROR")

        if translation and voice and str(voice).lower() != "none":
            # Kick off TTS asynchronously (fire-and-forget)
            tts_queue.put((
                translation,
                voice,
                settings_snapshot,
                output_device_idx,
                None
            ))
        elif translation:
            core.log_message("Voice set to text-only; skipping TTS enqueue.", "DEBUG")

        # Notify UI polling loop that translation finished (success or failure)
        translation_results_queue.put((transcription_id, transcription, translation))

    future.add_done_callback(_on_complete)

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

            if not voice or str(voice).lower() == "none":
                core.log_message("TTS worker received text-only task; skipping audio.", "DEBUG")
                if result_queue is not None:
                    result_queue.put((True, "Voice disabled; no audio generated"))
                tts_queue.task_done()
                continue

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
    
    # Translate synchronously for single-chunk processing
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
    if selected_voice and str(selected_voice).lower() != "none":
        loop = get_event_loop()
        loop.run_until_complete(core.text_to_speech_async(
            translation, 
            selected_voice,
            current_settings
        ))
    else:
        core.log_message("Voice set to text-only; skipping synchronous TTS.", "DEBUG")
    
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
    
    transcription_id = next_transcription_id()
    schedule_translation_task(
        transcription_id,
        transcription,
        actual_source_lang_name,
        target_language,
        ollama_model,
        voice,
        None
    )
    
    # Poll for the corresponding translation result before returning
    try:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                tid, trans_text, translation = translation_results_queue.get(timeout=0.1)
                translation_results_queue.task_done()
                if tid == transcription_id and translation:
                    return trans_text, translation, None
                else:
                    # Not ours; push back for continuous mode to pick up
                    translation_results_queue.put((tid, trans_text, translation))
            except queue.Empty:
                continue
    except Exception as e:
        core.log_message(f"Error waiting for translation result: {e}", "ERROR")
    
    return transcription, "Translation pending", None


def start_continuous_recording(source_language, target_language, ollama_model, voice, device_idx):
    """Start continuous recording for real-time translation."""
    global recording_thread, stop_event, recording_should_run, recording_params
    
    if recording_thread and recording_thread.is_alive():
        return "Recording is already in progress."
    
    # Ensure TTS worker is running before starting recording
    start_tts_worker()
    
    recording_should_run = True
    recording_params = (source_language, target_language, ollama_model, voice, device_idx)
    stop_event.clear()
    
    # Start recording thread
    recording_thread = threading.Thread(
        target=record_audio,
        args=(device_idx, audio_queue, stop_event),
        daemon=True
    )
    recording_thread.start()
    
    return "Started continuous recording. Speak now..."


def stop_continuous_recording(clear_intent=True):
    """Stop the continuous recording."""
    global recording_thread, stop_event, recording_should_run, recording_params
    
    if not recording_thread or not recording_thread.is_alive():
        return "No recording in progress."
    
    stop_event.set()
    recording_thread.join(timeout=2.0)
    recording_thread = None
    
    if clear_intent:
        recording_should_run = False
        recording_params = None
    return "Recording stopped."


# --- Audio Processing State Variables ---
audio_buffer = CircularAudioBuffer(max_duration_seconds=20)  # Use circular buffer
silence_counter = 0.0
is_speaking = False
last_transcription = ""

def check_audio_queue(source_language, target_language, ollama_model, voice, output_device=None):
    """Check for new audio in the queue and process it using sophisticated buffer management."""
    core.log_message(f"Checking audio queue with params: {source_language}, {target_language}, {ollama_model}, {voice}, {output_device}")
    
    global audio_buffer, silence_counter, is_speaking, last_transcription, whisper_model, last_displayed_transcription_id
    
    # First, surface any completed translations so UI displays them ASAP
    latest_result = None
    while True:
        try:
            result = translation_results_queue.get_nowait()
            translation_results_queue.task_done()
            transcription_id, transcription, translation = result
            if translation:
                latest_result = result
        except queue.Empty:
            break
        except Exception as e:
            core.log_message(f"Error draining translation results queue: {e}", "ERROR")
            break
    if latest_result:
        transcription_id, transcription, translation = latest_result
        if transcription_id > last_displayed_transcription_id:
            last_displayed_transcription_id = transcription_id
            return transcription, translation, None
    
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
                
                transcription_id = next_transcription_id()
                schedule_translation_task(
                    transcription_id,
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    voice,
                    output_device_idx
                )
                
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
                
                return transcription, None, None
            
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
    # OPTIMIZATION: Group chunks by sample rate to batch resample (reduces CPU overhead)
    chunks_by_sr = {}
    for ch in chunks:
        try:
            if isinstance(ch, tuple) and len(ch) == 2:
                data, sr = ch
            else:
                data, sr = ch, core.TARGET_RATE
            
            sr = int(sr)
            if sr not in chunks_by_sr:
                chunks_by_sr[sr] = []
            
            # Just collect raw numpy arrays first
            chunks_by_sr[sr].append(np.asarray(data, dtype=np.float32).flatten())
        except Exception as ce:
            core.log_message(f"Error preparing audio chunk: {ce}", "ERROR")

    resampled_parts = []
    for sr, data_list in chunks_by_sr.items():
        if not data_list:
            continue
        
        # Concatenate all raw audio for this sample rate first
        raw_combined = np.concatenate(data_list)
        
        if sr != core.TARGET_RATE:
            try:
                # Resample the big chunk once (Much faster than resampling many tiny chunks)
                processed = efficient_resample(raw_combined, sr, core.TARGET_RATE)
                resampled_parts.append(processed)
            except Exception as re:
                core.log_message(f"Batch resample {sr}->{core.TARGET_RATE} failed: {re}", "WARNING")
                continue
        else:
            resampled_parts.append(raw_combined)

    if not resampled_parts:
        return None, None, None
        
    # Final combine of all parts (usually just one part)
    audio_chunk = np.concatenate(resampled_parts).flatten().astype(np.float32)
    actual_duration = len(audio_chunk) / core.TARGET_RATE
    
    # Check if this is speech using configured energy threshold
    min_energy = get_pref_value(
        "speech_energy_threshold",
        0.0008,
        min_value=0.0001,
        max_value=0.01,
        cast_type=float
    )
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
                
                transcription_id = next_transcription_id()
                schedule_translation_task(
                    transcription_id,
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    voice,
                    output_device_idx
                )
                
                # Keep a portion of the buffer for overlap to prevent word loss
                overlap_audio = audio_buffer.get_overlap(BUFFER_OVERLAP)
                audio_buffer.clear()
                if len(overlap_audio) > 0:
                    audio_buffer.add_audio(overlap_audio)
                
                last_transcription = transcription
                
                return transcription, None, None
            
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
                
                transcription_id = next_transcription_id()
                schedule_translation_task(
                    transcription_id,
                    transcription,
                    actual_source_lang_name,
                    target_language,
                    ollama_model,
                    voice,
                    output_device_idx
                )
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

    with gr.Blocks(title="GoGospleNow.com") as app:
        # Header row with title and dark mode toggle
        with gr.Row():
            with gr.Column(scale=6):
                gr.Markdown("# GoGospleNow.com")
                gr.Markdown("Real Time Preaching Translator")
            with gr.Column(scale=1, min_width=200):
                # Theme toggle - pure HTML links, no JavaScript needed
                gr.HTML(
                    """
                    <style>
                    .theme-links {
                        display: flex;
                        gap: 8px;
                        justify-content: flex-end;
                        padding: 10px 0;
                    }
                    .theme-link {
                        padding: 6px 12px;
                        border-radius: 15px;
                        text-decoration: none !important;
                        font-size: 13px;
                        font-weight: 500;
                        transition: all 0.2s ease;
                    }
                    .theme-link-dark {
                        background: #1f2937;
                        color: #e5e7eb !important;
                        border: 1px solid #374151;
                    }
                    .theme-link-dark:hover {
                        background: #374151;
                    }
                    .theme-link-light {
                        background: #f3f4f6;
                        color: #374151 !important;
                        border: 1px solid #d1d5db;
                    }
                    .theme-link-light:hover {
                        background: #e5e7eb;
                    }
                    </style>
                    <div class="theme-links">
                        <a class="theme-link theme-link-dark" href="?__theme=dark">🌙 Dark</a>
                        <a class="theme-link theme-link-light" href="?__theme=light">☀️ Light</a>
                    </div>
                    """
                )

        gr.HTML(
            """
            <style>
            /* Modern, sleek button styles */
            .launch-display-btn button:not([disabled]) { 
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                color: #fff; 
                border: none; 
                border-radius: 8px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: all 0.2s ease;
            }
            .launch-display-btn button:not([disabled]):hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.15), 0 3px 6px -1px rgba(0, 0, 0, 0.1);
            }
            .launch-display-btn button[disabled] { background: #e5e7eb !important; color: #9ca3af !important; border: 1px solid #d1d5db !important; }
            
            .close-display-btn button:not([disabled]) { 
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                color: #fff; 
                border: none; 
                border-radius: 8px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: all 0.2s ease;
            }
            .close-display-btn button:not([disabled]):hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.15);
            }
            .close-display-btn button[disabled] { background: #e5e7eb !important; color: #9ca3af !important; border: 1px solid #d1d5db !important; }
            
            /* Orange buttons for Save Server Settings and Apply Sync Settings */
            .orange-button button { 
                background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important; 
                color: #fff !important; 
                border: none !important; 
                border-radius: 8px !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
                transition: all 0.2s ease !important;
            }
            .orange-button button:hover { 
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.15) !important;
            }
            
            /* Screen size button highlighting on click */
            #ratio_16_9_hd:active, #ratio_16_9_fhd:active, #ratio_16_10:active, #ratio_4_3:active {
                background: #10b981 !important;
                color: #fff !important;
                transform: scale(0.98);
            }
            
            /* General UI polish */
            .gradio-container { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
            footer { display: none !important; } /* Hide Gradio footer for cleaner look */
            </style>
            """
        )

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
                        default_provider_trans = user_preferences.get("translation_provider", "Ollama")
                        cont_translation_provider = gr.Dropdown(
                            choices=["Ollama", "OpenAI", "Groq", "Grok (xAI)", "Mistral", "Custom OpenAI"],
                            value=default_provider_trans,
                            label="Translation Provider",
                            interactive=True
                        )

                        default_model = user_preferences.get("ollama_model", "")
                        if not default_model and available_ollama_models:
                            default_model = available_ollama_models[0]
                            
                        cont_ollama_model = gr.Dropdown(
                            choices=available_ollama_models,
                            value=default_model,
                            label="AI Translation Model",
                            allow_custom_value=True
                        )
                        
                        def update_model_choices(provider):
                            # Merge current in-memory settings with provider change
                            # This ensures API keys from the settings file are available
                            global current_settings
                            
                            # First, load fresh settings from file to get API keys
                            file_settings = core.load_settings()
                            
                            # Update in-memory settings
                            if current_settings is None:
                                current_settings = file_settings.copy()
                            else:
                                # Merge: keep file's API keys, update provider
                                for key in ['openai_api_key', 'groq_api_key', 'grok_api_key', 'mistral_api_key', 'custom_openai_url', 'custom_openai_key']:
                                    if key in file_settings:
                                        current_settings[key] = file_settings[key]
                            
                            # Set the new provider
                            current_settings["translation_provider"] = provider
                            user_preferences["translation_provider"] = provider
                            
                            # Fetch new models with the merged settings
                            new_models = core.fetch_available_models(current_settings=current_settings)
                            new_val = new_models[0] if new_models else ""
                            core.log_message(f"Provider changed to {provider}, fetched {len(new_models)} models")
                            return gr.update(choices=new_models, value=new_val)

                        cont_translation_provider.change(
                            fn=update_model_choices,
                            inputs=[cont_translation_provider],
                            outputs=[cont_ollama_model]
                        )
                        
                        # TTS Provider Selection
                        default_provider = user_preferences.get("tts_provider", "Kokoro")
                        cont_tts_provider = gr.Dropdown(
                            choices=["Kokoro", "Google"],
                            value=default_provider,
                            label="TTS Provider",
                            info="Select Kokoro (Local) or Google (Cloud)"
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
                        # Function to build voice list based on provider
                        def get_voice_choices(provider):
                            choices = [("Text Only — no TTS", "none")]
                            if provider == "Google":
                                # Language and country mapping for Google voices
                                lang_map = {
                                    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
                                    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "cmn": "Chinese (Mandarin)",
                                    "ru": "Russian", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "bn": "Bengali",
                                    "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
                                    "ar": "Arabic", "nl": "Dutch", "pl": "Polish", "tr": "Turkish", "sv": "Swedish",
                                    "nb": "Norwegian", "da": "Danish", "fi": "Finnish", "el": "Greek", "cs": "Czech",
                                    "sk": "Slovak", "uk": "Ukrainian", "vi": "Vietnamese", "id": "Indonesian",
                                    "th": "Thai", "fil": "Filipino", "af": "Afrikaans"
                                }
                                country_map = {
                                    "US": "US", "GB": "UK", "AU": "AU", "IN": "IN", "ES": "ES", "FR": "FR", "CA": "CA",
                                    "DE": "DE", "IT": "IT", "BR": "BR", "PT": "PT", "JP": "JP", "KR": "KR",
                                    "CN": "CN", "TW": "TW", "RU": "RU", "XA": "XA", "NL": "NL", "PL": "PL",
                                    "TR": "TR", "SE": "SE", "NO": "NO", "DK": "DK", "FI": "FI", "GR": "GR",
                                    "CZ": "CZ", "SK": "SK", "UA": "UA", "VN": "VN", "ID": "ID", "TH": "TH", "PH": "PH",
                                    "ZA": "ZA"
                                }
                                
                                for v in core.GOOGLE_VOICES:
                                    parts = v.split("-")
                                    lang_code = parts[0] if len(parts) > 0 else ""
                                    country_code = parts[1] if len(parts) > 1 else ""
                                    voice_type = parts[2] if len(parts) > 2 else ""
                                    voice_id = parts[3] if len(parts) > 3 else ""
                                    
                                    language = lang_map.get(lang_code, lang_code.upper())
                                    country = country_map.get(country_code, country_code)
                                    
                                    # Create readable label: "English (US) - Neural2-A"
                                    label = f"{language} ({country}) - {voice_type}-{voice_id}" if voice_type else f"{language} ({country})"
                                    choices.append((label, v))
                                
                                # Sort Google voices alphabetically by label (skip "Text Only" at index 0)
                                choices[1:] = sorted(choices[1:], key=lambda x: x[0])
                            else:  # Kokoro
                                for v in core.KOKORO_VOICES:
                                    choices.append((f"{v} — {voice_country_map.get(v, 'Unknown')}", v))
                            return choices
                        
                        # Build initial voice list
                        labeled_voice_choices = get_voice_choices(default_provider)
                        voice_choice_values = [value for _, value in labeled_voice_choices]
                        default_voice_choice = user_preferences.get("voice", "em_alex")
                        if default_voice_choice not in voice_choice_values:
                            default_voice_choice = labeled_voice_choices[1][1] if len(labeled_voice_choices) > 1 else "none"

                        cont_voice = gr.Dropdown(
                            choices=labeled_voice_choices,
                            value=default_voice_choice,
                            label="Audio Output Voice",
                            info="Should match Translation Target Language"
                        )
                        
                        # Update voice list when provider changes
                        def update_voice_list(provider):
                            global current_settings, user_preferences
                            if current_settings:
                                current_settings["tts_provider"] = provider
                            user_preferences["tts_provider"] = provider
                            new_choices = get_voice_choices(provider)
                            new_val = new_choices[1][1] if len(new_choices) > 1 else "none"
                            return gr.update(choices=new_choices, value=new_val)
                        
                        cont_tts_provider.change(
                            fn=update_voice_list,
                            inputs=[cont_tts_provider],
                            outputs=[cont_voice]
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

                    def _toggle_translation_display(launch=True, *args):
                        manager = ensure_translation_display_manager()
                        if launch:
                            # If arguments are provided (from Launch button), update preferences first
                            if args and len(args) == 16:
                                font, font_size, font_color, bg_color, monitor_idx, manual_x, manual_y, width, height, pos_x, pos_y, always_on_top, history_size, hold_seconds, h_align, v_align = args
                                global user_preferences
                                user_preferences.update({
                                    "display_font_family": font,
                                    "display_font_size": int(font_size),
                                    "display_font_color": font_color,
                                    "display_bg_color": bg_color,
                                    "display_monitor": int(monitor_idx),
                                    "display_manual_offset_x": int(manual_x),
                                    "display_manual_offset_y": int(manual_y),
                                    "display_window_width": int(width),
                                    "display_window_height": int(height),
                                    "display_window_x": int(pos_x),
                                    "display_window_y": int(pos_y),
                                    "display_always_on_top": bool(always_on_top),
                                    "display_history_size": int(history_size),
                                    "display_hold_seconds": float(hold_seconds),
                                    "display_horizontal_align": h_align,
                                    "display_vertical_align": v_align,
                                })
                                # Optionally save to disk
                                save_user_preferences(user_preferences)

                            config = get_translation_display_config()
                            # Note: launch() will resolve monitor coordinates including all_monitors for 'm' key cycling
                            
                            if latest_translation_text:
                                manager.update_text(latest_translation_text)
                            ok, message = manager.launch(config)
                            if ok:
                                return [gr.Button(interactive=False), gr.Button(interactive=True), message]
                            return [gr.Button(interactive=True), gr.Button(interactive=False), message]
                        
                        # Closing
                        ok, message = manager.close()
                        return [gr.Button(interactive=True), gr.Button(interactive=False), message]

                    launch_display_btn = gr.Button("Launch Translation Display", elem_classes=["launch-display-btn"])
                    close_display_btn = gr.Button("Close Translation Display", interactive=False, elem_classes=["close-display-btn"])
                    display_status = gr.Textbox(label="Display Status", interactive=False)

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
            def start_and_save_prefs(source_lang, target_lang, trans_provider, model, tts_provider, voice_choice, input_device_name, output_device_name):
                # Save preferences including device selections
                global user_preferences, current_settings
                user_preferences.update({
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "translation_provider": trans_provider,
                    "ollama_model": model,
                    "tts_provider": tts_provider,
                    "voice": voice_choice,
                    "input_device": input_device_name,
                    "output_device": output_device_name
                })
                save_user_preferences(user_preferences)
                
                # Reload settings from file to get API keys, then merge with UI selections
                file_settings = core.load_settings()
                if current_settings is None:
                    current_settings = file_settings.copy()
                else:
                    # Merge API keys from file (in case they were saved via Settings tab)
                    for key in ['openai_api_key', 'groq_api_key', 'grok_api_key', 'mistral_api_key', 
                                'custom_openai_url', 'custom_openai_key', 'google_api_key',
                                'translation_server', 'tts_server_url']:
                        if key in file_settings:
                            current_settings[key] = file_settings[key]
                
                # Update runtime settings with UI selections
                current_settings["tts_provider"] = tts_provider
                current_settings["translation_provider"] = trans_provider
                
                core.log_message(f"Starting translation with provider: {trans_provider}, model: {model}")
                
                # Start recording with selected device
                result = start_with_selected_device(source_lang, target_lang, model, voice_choice, input_device_name, output_device_name)
                if not result.startswith("Error"):
                    return [gr.Button(interactive=False), gr.Button(interactive=True), gr.update(active=True)]
                return [gr.Button(interactive=True), gr.Button(interactive=False), gr.update(active=False)]
            
            # Server-side polling via Gradio Timer (avoids relying on browser JS)
            continuous_timer = gr.Timer(0.2, active=False)

            start_btn.click(
                fn=start_and_save_prefs,
                inputs=[cont_source_language, cont_target_language, cont_translation_provider, cont_ollama_model, cont_tts_provider, cont_voice, cont_input_device, cont_output_device],
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
                        broadcast_translation_to_display(translation)
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
            
            # Check if API keys are set via environment variables
            def get_api_key_status(env_var_name, setting_key, display_name):
                env_key = os.getenv(env_var_name)
                if env_key:
                    return f"✅ **{display_name}:** Using `{env_var_name}` environment variable (recommended)"
                elif current_settings.get(setting_key):
                    return f"⚠️ **{display_name}:** Using settings.json (consider `{env_var_name}` env var)"
                else:
                    return f"❌ **{display_name}:** Not configured"
            
            # Build status for all API keys
            api_statuses = [
                get_api_key_status("GOOGLE_API_KEY", "google_api_key", "Google TTS"),
                get_api_key_status("OPENAI_API_KEY", "openai_api_key", "OpenAI"),
                get_api_key_status("GROQ_API_KEY", "groq_api_key", "Groq"),
                get_api_key_status("XAI_API_KEY", "grok_api_key", "Grok (xAI)"),
                get_api_key_status("MISTRAL_API_KEY", "mistral_api_key", "Mistral"),
            ]
            
            gr.Markdown("### API Key Status\n" + "\n\n".join(api_statuses))
            gr.Markdown("*For better security, set API keys as environment variables instead of storing in settings.json*")
            
            with gr.Row():
                google_api_key = gr.Textbox(
                    value=current_settings.get("google_api_key", ""),
                    label="Google Cloud API Key",
                    type="password",
                    info="Or set GOOGLE_API_KEY environment variable",
                    placeholder="Leave empty if using environment variable"
                )
            
            with gr.Row():
                openai_api_key = gr.Textbox(
                    value=current_settings.get("openai_api_key", ""),
                    label="OpenAI API Key",
                    type="password",
                    info="Or set OPENAI_API_KEY environment variable",
                    placeholder="Leave empty if using environment variable"
                )
                groq_api_key = gr.Textbox(
                    value=current_settings.get("groq_api_key", ""),
                    label="Groq API Key",
                    type="password",
                    info="Or set GROQ_API_KEY environment variable",
                    placeholder="Leave empty if using environment variable"
                )
            
            with gr.Row():
                grok_api_key = gr.Textbox(
                    value=current_settings.get("grok_api_key", ""),
                    label="Grok (xAI) API Key",
                    type="password",
                    info="Or set XAI_API_KEY environment variable",
                    placeholder="Leave empty if using environment variable"
                )
                mistral_api_key = gr.Textbox(
                    value=current_settings.get("mistral_api_key", ""),
                    label="Mistral API Key",
                    type="password",
                    info="Or set MISTRAL_API_KEY environment variable",
                    placeholder="Leave empty if using environment variable"
                )
            
            def save_settings(translation_url, tts_url, google_key, openai_key, groq_key, grok_key, mistral_key):
                new_settings = {
                    "translation_server": translation_url,
                    "tts_server_url": tts_url,
                    "google_api_key": google_key,
                    "openai_api_key": openai_key,
                    "groq_api_key": groq_key,
                    "grok_api_key": grok_key,
                    "mistral_api_key": mistral_key,
                    # Include translation_provider from user_preferences if set
                    "translation_provider": user_preferences.get("translation_provider", "Ollama")
                }
                
                try:
                    # Preserve existing keys that aren't in this form
                    if os.path.exists(core.SETTINGS_FILE):
                        with open(core.SETTINGS_FILE, "r") as f:
                            existing = json.load(f)
                            # Merge new with existing, new takes precedence
                            for k, v in new_settings.items():
                                existing[k] = v
                            new_settings = existing

                    with open(core.SETTINGS_FILE, "w") as f:
                        json.dump(new_settings, f, indent=4)
                    
                    global current_settings
                    current_settings = new_settings
                    
                    # Refresh Models (using new provider logic and settings)
                    global available_ollama_models
                    available_ollama_models = core.fetch_available_models(server_url=translation_url, current_settings=new_settings)
                    
                    return f"Settings saved successfully. Models refreshed."
                except Exception as e:
                    return f"Error saving settings: {e}"
            
            save_btn = gr.Button("Save Server Settings", variant="primary", elem_classes=["orange-button"])
            settings_status = gr.Textbox(label="Status")
            
            save_btn.click(
                fn=save_settings,
                inputs=[translation_server, tts_server, google_api_key, openai_api_key, groq_api_key, grok_api_key, mistral_api_key],
                outputs=[settings_status]
            )

            gr.Markdown("---")
            gr.Markdown("## Translation Display Settings")

            display_config = get_translation_display_config()

            with gr.Row():
                display_font = gr.Dropdown(
                    choices=DISPLAY_FONT_CHOICES,
                    value=display_config["display_font_family"],
                    label="Font Family"
                )
                display_font_size = gr.Slider(
                    minimum=16,
                    maximum=200,
                    step=2,
                    value=display_config["display_font_size"],
                    label="Font Size"
                )
                display_font_color = gr.ColorPicker(
                    value=display_config["display_font_color"],
                    label="Font Color"
                )

            gr.Markdown("### Quick Aspect Ratio Presets")
            gr.Markdown("Click a preset to set common display resolutions, or use the sliders below for custom sizes.")
            
            # State to track which button was clicked
            selected_ratio = gr.State(value=None)
            
            with gr.Row():
                ratio_16_9_hd = gr.Button("16:9 HD (1280x720)", size="sm", elem_id="ratio_16_9_hd")
                ratio_16_9_fhd = gr.Button("16:9 Full HD (1920x1080)", size="sm", elem_id="ratio_16_9_fhd")
                ratio_16_10 = gr.Button("16:10 (1920x1200)", size="sm", elem_id="ratio_16_10")
                ratio_4_3 = gr.Button("4:3 (1600x1200)", size="sm", elem_id="ratio_4_3")

            with gr.Row():
                display_bg_color = gr.ColorPicker(
                    value=display_config["display_bg_color"],
                    label="Background Color (use #00000000 for transparent)"
                )
                transparent_bg_btn = gr.Button("Set Transparent", size="sm")
                
                # Detect available monitors for better UX
                monitor_choices = [(f"Monitor {i+1}", str(i)) for i in range(4)]  # fallback
                if get_monitors:
                    try:
                        monitors = list(get_monitors())
                        # Sort by X position (left to right) for intuitive numbering
                        sorted_monitors = sorted(enumerate(monitors), key=lambda x: x[1].x)
                        monitor_choices = []
                        for display_num, (orig_idx, m) in enumerate(sorted_monitors):
                            # Simple labels: Monitor 1, Monitor 2, Monitor 3 (PRIMARY noted)
                            if m.is_primary:
                                label = f"Monitor {display_num+1} (PRIMARY)"
                            else:
                                label = f"Monitor {display_num+1}"
                            # Store ORIGINAL index since that's what screeninfo uses internally
                            monitor_choices.append((label, str(orig_idx)))
                    except Exception:
                        pass  # Use fallback choices

                display_monitor = gr.Dropdown(
                    choices=monitor_choices,
                    value=str(display_config.get("display_monitor", "0")),
                    label="Target Monitor",
                    info="Select the screen to project onto."
                )
            
            with gr.Row():
                display_manual_x = gr.Number(
                    value=display_config.get("display_manual_offset_x", 0),
                    label="Manual X Offset (Override)",
                    info="If auto-detection fails, set this to 1920 (or -1920) to move window right/left."
                )
                display_manual_y = gr.Number(
                    value=display_config.get("display_manual_offset_y", 0),
                    label="Manual Y Offset (Override)",
                    info="Usually 0, unless monitors are stacked vertically."
                )
            
            with gr.Row():
                display_width = gr.Slider(
                    minimum=400,
                    maximum=3840,
                    step=10,
                    value=display_config["display_window_width"],
                    label="Window Width (Custom)"
                )
                display_height = gr.Slider(
                    minimum=200,
                    maximum=2160,
                    step=10,
                    value=display_config["display_window_height"],
                    label="Window Height (Custom)"
                )
            
            # Define preset ratio functions with feedback
            def set_ratio_16_9_hd():
                return 1280, 720, "16:9 HD selected"
            
            def set_ratio_16_9_fhd():
                return 1920, 1080, "16:9 Full HD selected"
            
            def set_ratio_16_10():
                return 1920, 1200, "16:10 selected"
            
            def set_ratio_4_3():
                return 1600, 1200, "4:3 selected"
            
            def set_transparent_bg():
                return "#00000000"
            
            # Status indicator for ratio selection
            ratio_status = gr.Textbox(label="Screen Size Selection", value="", interactive=False, visible=True)
            
            # Connect preset buttons to update width/height sliders with feedback
            ratio_16_9_hd.click(fn=set_ratio_16_9_hd, outputs=[display_width, display_height, ratio_status])
            ratio_16_9_fhd.click(fn=set_ratio_16_9_fhd, outputs=[display_width, display_height, ratio_status])
            ratio_16_10.click(fn=set_ratio_16_10, outputs=[display_width, display_height, ratio_status])
            ratio_4_3.click(fn=set_ratio_4_3, outputs=[display_width, display_height, ratio_status])
            transparent_bg_btn.click(fn=set_transparent_bg, outputs=[display_bg_color])

            with gr.Row():
                display_pos_x = gr.Number(
                    value=display_config["display_window_x"],
                    label="Window X Position"
                )
                display_pos_y = gr.Number(
                    value=display_config["display_window_y"],
                    label="Window Y Position"
                )
                display_on_top = gr.Checkbox(
                    value=display_config["display_always_on_top"],
                    label="Always On Top"
                )
                display_history = gr.Slider(
                    minimum=1,
                    maximum=6,
                    step=1,
                    value=display_config["display_history_size"],
                    label="Lines to Keep Visible"
                )
                display_hold = gr.Slider(
                    minimum=0.0,
                    maximum=10.0,
                    step=0.1,
                    value=display_config["display_hold_seconds"],
                    label="Seconds Before Clearing",
                    info="Keep translations visible for at least this many seconds."
                )

            with gr.Row():
                display_h_align = gr.Dropdown(
                    choices=ALIGN_HORIZONTAL_CHOICES,
                    value=display_config["display_horizontal_align"],
                    label="Horizontal Alignment"
                )
                display_v_align = gr.Dropdown(
                    choices=ALIGN_VERTICAL_CHOICES,
                    value=display_config["display_vertical_align"],
                    label="Vertical Alignment"
                )

            display_save_btn = gr.Button("Save Display Settings", variant="primary")
            display_save_status = gr.Textbox(label="Display Settings Status")

            def save_display_settings(font, font_size, font_color, bg_color, monitor_idx, manual_x, manual_y, width, height, pos_x, pos_y, always_on_top, history_size, hold_seconds, h_align, v_align):
                global user_preferences
                user_preferences.update({
                    "display_font_family": font,
                    "display_font_size": int(font_size),
                    "display_font_color": font_color,
                    "display_bg_color": bg_color,
                    "display_monitor": int(monitor_idx),
                    "display_manual_offset_x": int(manual_x),
                    "display_manual_offset_y": int(manual_y),
                    "display_window_width": int(width),
                    "display_window_height": int(height),
                    "display_window_x": int(pos_x),
                    "display_window_y": int(pos_y),
                    "display_always_on_top": bool(always_on_top),
                    "display_history_size": int(history_size),
                    "display_hold_seconds": float(hold_seconds),
                    "display_horizontal_align": h_align,
                    "display_vertical_align": v_align,
                })
                save_user_preferences(user_preferences)
                cfg = get_translation_display_config()
                
                # Resolve monitor coordinates in main process before sending to display
                if get_monitors:
                    try:
                        monitors = get_monitors()
                        # Pass ALL monitor info so 'm' key cycling works
                        all_monitors = []
                        for m in monitors:
                            all_monitors.append({
                                "x": m.x, "y": m.y, 
                                "width": m.width, "height": m.height,
                                "is_primary": m.is_primary
                            })
                        cfg["all_monitors"] = all_monitors
                        
                        idx = int(cfg.get("display_monitor", 0))
                        if 0 <= idx < len(monitors):
                            m = monitors[idx]
                            cfg["monitor_x"] = m.x
                            cfg["monitor_y"] = m.y
                            cfg["monitor_width"] = m.width
                            cfg["monitor_height"] = m.height
                            core.log_message(f"Settings: Resolved Monitor {idx} to X={m.x}, Y={m.y}, Size={m.width}x{m.height}")
                    except Exception as e:
                        core.log_message(f"Settings: Monitor resolution failed: {e}", "WARNING")
                
                manager = ensure_translation_display_manager()
                manager.apply_config(cfg)
                return "Display settings saved."

            display_save_btn.click(
                fn=save_display_settings,
                inputs=[
                    display_font,
                    display_font_size,
                    display_font_color,
                    display_bg_color,
                    display_monitor,
                    display_manual_x,
                    display_manual_y,
                    display_width,
                    display_height,
                    display_pos_x,
                    display_pos_y,
                    display_on_top,
                    display_history,
                    display_hold,
                    display_h_align,
                    display_v_align,
                ],
                outputs=[display_save_status],
                show_progress=False,
            )

            gr.Markdown("Use these options to control the look and placement of the external translation-only screen.")

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
                    value=get_pref_value("cpu_threads", 2, min_value=1, max_value=12, cast_type=int),
                    label="CPU Threads (lower = less CPU usage)",
                    info="Threads for compute libs. Lower = less CPU use; higher = faster on multi-core CPUs."
                )
                s_processing_batch = gr.Slider(
                    minimum=1, maximum=5, step=1,
                    value=get_pref_value("processing_batch_size", 1, min_value=1, max_value=5, cast_type=int),
                    label="Audio Batch Size (higher = more efficient, higher latency)",
                    info="Process multiple chunks together. Higher = more efficient, slightly higher latency."
                )
            with gr.Row():
                s_translation_workers = gr.Slider(
                    minimum=1, maximum=8, step=1,
                    value=get_pref_value("translation_workers", DEFAULT_TRANSLATION_WORKERS, min_value=1, max_value=8, cast_type=int),
                    label="Parallel Translation Workers",
                    info="Higher = more simultaneous translations (needs more CPU/network)."
                )
                s_buffer_size = gr.Slider(
                    minimum=10, maximum=60, step=5,
                    value=get_pref_value("buffer_duration_s", 20, min_value=10, max_value=60, cast_type=int),
                    label="Audio Buffer Duration (s)",
                    info="Max running buffer length for detection. Longer = more context but more memory."
                )
            with gr.Row():
                s_energy_threshold = gr.Slider(
                    minimum=0.0001, maximum=0.01, step=0.0001,
                    value=get_pref_value("speech_energy_threshold", 0.0008, min_value=0.0001, max_value=0.01, cast_type=float),
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
                    was_recording = is_recording_active()
                    if was_recording:
                        stop_continuous_recording(clear_intent=False)
                    reload_whisper_model(force=True)
                    restart_recording_if_needed(was_recording)
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
            
            # Preset dropdown hidden - always use Custom mode with manual slider settings
            # The other presets are not accurate for all hardware configurations
            with gr.Row(visible=False):
                preset_dropdown = gr.Dropdown(
                    choices=["Custom"],
                    value="Custom",
                    label="Performance Preset",
                    info="Using custom settings from sliders above."
                )
            
            gr.Markdown("---")
            gr.Markdown("## 💾 Apply & Save All Settings")
            
            # Single unified status display
            unified_status = gr.Textbox(label="Settings Status", lines=3, info="Status and messages from applying settings.")
            
            def apply_all_settings(block_ms, overlap_ms, min_sil_ms, min_speech_ms, max_speech_s, 
                                 no_speech_th, vad_enabled, cpu_threads, batch_size, translation_workers, buffer_duration, 
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
                    # Enforce thread limits at runtime using threadpoolctl
                    threadpoolctl.threadpool_limits(limits=int(cpu_threads))
                    
                    worker_count = max(1, min(8, int(translation_workers)))
                    refresh_translation_executor(worker_count)

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
                        "translation_workers": worker_count,
                        "buffer_duration_s": int(buffer_duration),
                        "speech_energy_threshold": float(energy_threshold),
                        "compute_device": device,
                        "compute_type": compute_type,
                        "whisper_model_size": str(whisper_model_size)
                    })
                    
                    # DEBUG: Confirm what was saved
                    core.log_message(f"DEBUG: Saved vad_filter in user_preferences: {user_preferences.get('vad_filter')}")
                    
                    # Force Whisper model reload with new hardware/model settings
                    try:
                        was_recording = is_recording_active()
                        if was_recording:
                            stop_continuous_recording(clear_intent=False)
                        new_model = reload_whisper_model(force=True)
                        actual_device = getattr(new_model.model, 'device', 'unknown')
                        core.log_message(f"Whisper model reloaded: size={core.WHISPER_MODEL_SIZE}, device={actual_device}, precision={user_preferences.get('compute_type')}")
                    except Exception as e:
                        core.log_message(f"Failed to reload Whisper model: {e}", "WARNING")
                    else:
                        restart_recording_if_needed(was_recording)
                    
                    # Save all preferences
                    save_user_preferences(user_preferences)
                    
                    messages.extend([
                        "✅ Timing settings applied",
                        f"✅ VAD settings applied: threshold={float(no_speech_th)}, filter={'ON' if bool(vad_enabled) else 'OFF'}",
                        "✅ CPU & translation worker settings applied",
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
                    s_no_speech, s_vad_filter, s_cpu_threads, s_processing_batch, s_translation_workers,
                    s_buffer_size, s_energy_threshold, device_dropdown, compute_type_dropdown, whisper_model_dropdown, preset_dropdown
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
            apply_sync_btn = gr.Button("Apply Sync Settings", variant="primary", elem_classes=["orange-button"])
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
            
            logs_output = gr.Textbox(label="Today's Logs", lines=20, max_lines=30)
            refresh_logs = gr.Button("Refresh Logs")
            
            refresh_logs.click(
                fn=get_logs,
                inputs=[],
                outputs=[logs_output]
            )

            # --- Event Wiring (Moved here to ensure all inputs are defined) ---
            launch_display_btn.click(
                fn=lambda *args: _toggle_translation_display(True, *args),
                inputs=[
                    display_font,
                    display_font_size,
                    display_font_color,
                    display_bg_color,
                    display_monitor,
                    display_manual_x,
                    display_manual_y,
                    display_width,
                    display_height,
                    display_pos_x,
                    display_pos_y,
                    display_on_top,
                    display_history,
                    display_hold,
                    display_h_align,
                    display_v_align,
                ],
                outputs=[launch_display_btn, close_display_btn, display_status],
            )        
        close_display_btn.click(
            fn=lambda: _toggle_translation_display(False),
            inputs=[],
            outputs=[launch_display_btn, close_display_btn, display_status],
        )
    
    return app


# --- Main Function ---
def create_app():
    gradio_ui = create_ui()
    fastapi_app = FastAPI()

    @fastapi_app.get("/listener")
    async def get_listener():
        return FileResponse("listener.html")

    # Mount Gradio at the root
    return gr.mount_gradio_app(fastapi_app, gradio_ui, path="/")

if __name__ == "__main__":
    app = create_app()
    import uvicorn
    # Use uvicorn to run the FastAPI app which includes Gradio
    uvicorn.run(app, host="0.0.0.0", port=7860)
