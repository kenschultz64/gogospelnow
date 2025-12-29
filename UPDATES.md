# Updates – 2025-12-27

## Mobile Listener App (listener.html)
- **Congregation Listener:** A lightweight mobile web page that allows congregation members to view real-time translations and listen to audio on their own devices.
- **No Microphone Access:** The listener page does NOT access the phone's microphone – it only receives data from the server. No feedback loop is possible.
- **Performance:** The listener page is completely independent from the main translator. It won't slow down transcription, translation, or TTS.
- **Android Screen Timeout:** Due to Android's aggressive power management, JavaScript-based screen wake locks don't reliably work for long sessions (40+ minutes). The app now displays clear instructions for Android users to temporarily increase their screen timeout in Settings → Display → Screen timeout.
- **iOS Compatibility:** Works well on iPhone/iPad with Wake Lock API support.

---

# Updates – 2025-12-19

## Display Window Enhancements
- **Smart Monitor Selection:** Monitors are now numbered left-to-right (Monitor 1 = leftmost) for intuitive selection. The dropdown shows simple labels like "Monitor 1 (PRIMARY)", "Monitor 2", "Monitor 3".
- **Custom Window Sizes:** The display window now respects custom Width × Height settings from the sliders, allowing smaller windows (e.g., 1280×720 on a 1080p monitor).
- **Worship-Friendly Close Button:** Replaced the distracting red close button with a subtle, semi-transparent "×" that only appears on hover. Perfect for live worship settings.
- **Keyboard Shortcuts:** Press Escape to close the display window. Press 'M' to cycle through available monitors.
- **Cross-Platform Monitor Detection:** Uses the `screeninfo` library for consistent monitor detection on Windows, macOS, and Linux.

## Settings Simplification
- **Removed Performance Presets:** The preset dropdown is now hidden. All timing/VAD parameters are controlled directly via the manual sliders for maximum flexibility.

## Code Quality
- Improved debug logging for monitor selection troubleshooting.
- Fixed variable naming issues in the display subprocess.

---

# Updates – 2025-11-22

## Gradio Compatibility
- Removed the deprecated `theme` argument when constructing `gr.Blocks`, preventing crashes on Gradio 6.x while remaining compatible with older releases.

## Latency & Responsiveness
- Tuned default runtime parameters (smaller audio block size, shorter silence thresholds, tighter overlap) to push smaller chunks through the pipeline faster.
- Made the single-shot Gradio audio path fire-and-forget for TTS, matching the continuous mode’s responsiveness.
- Added a background translation executor with per-transcription IDs so transcription, translation, and TTS can overlap without losing buffered audio.
- Continuous polling now surfaces completed translations immediately, keeping the UI updated as soon as each translation finishes.

## Throughput Controls
- Translation executor defaults to four workers and can be re-created dynamically to keep up with real-time speech.
- Introduced a “Parallel Translation Workers” slider in the Settings tab; applying settings saves the count, refreshes the executor, and persists it per machine.

## Reliability
- All changes honor the existing user preferences system, so adjustments made in the Gradio UI still override defaults across macOS, Windows, and Linux deployments.

## External Translation Display & UI Enhancements
- Added an optional translation-only window driven by tkinter. It launches from the Speech Translator tab, can be positioned/aligned, and mirrors the latest translations with configurable font, colors, and hold duration.
- The display now runs in its own process for stability, works across macOS/Windows/Linux, and supports customizable history length plus per-line anchoring (left/right/top/bottom).
- Launch/close controls in the main UI now include distinct active/disabled states to make it obvious when the external screen is running.

## Dependency Note
- Documented that tkinter bindings must be present (Homebrew `python-tk@3.x`, `sudo apt install python3-tk`, Windows installer “tcl/tk” option) so the external display can start on all platforms.
