# GoGospelNow Application Settings Guide

This document provides a verbose description of every adjustable setting available in the **GoGospelNow** application. These settings allow you to fine-tune the performance, appearance, and behavior of the real-time translation system to match your specific hardware and presentation needs.

All settings can be found in the **Settings** tab of the web interface (`http://localhost:7860`).

---

## 1. Server Settings
These settings control how the application connects to the backend AI services.

*   **Translation Server URL**
    *   *Default:* `http://localhost:11434`
    *   *Description:* This is the address of the **Ollama** server running locally on your machine. Ollama is responsible for the actual translation logic (e.g., converting English text to Spanish).
    *   *Adjustment:* You typically do not need to change this unless you are running Ollama on a different computer on your network.

*   **TTS Server URL**
    *   *Default:* `http://localhost:8880/v1`
    *   *Description:* This is the address of the **Kokoro** Text-to-Speech server (running in Docker). This service generates the spoken audio for the translated text.
    *   *Adjustment:* Like the translation server, this usually stays at the default unless you have a custom network setup.

*   **Google Cloud API Key (Optional)**
    *   *Description:* If you wish to use Google Cloud's high-quality voices instead of the local Kokoro voices, you must provide an API key here.
    *   *Security Note:* It is recommended to set this via the `GOOGLE_API_KEY` environment variable for better security, rather than saving it in the application settings file.

---

## 2. Translation Display Settings
These settings control the appearance and behavior of the dedicated "Translation Display" window. This window is designed to be dragged onto a secondary screen (like a projector or confidence monitor) for the audience or speaker to read.

*   **Font Family**: Select the font style (e.g., Arial, Helvetica, Times New Roman) to match your branding or readability preferences.
*   **Font Size**: Controls the size of the text. Larger text is better for distant viewing (projectors), while smaller text fits more history.
*   **Font Color**: The color of the translated text (default is White).
*   **Background Color**: The background color of the window (default is Black).
    *   *Transparent Mode:* You can set this to `#00000000` (or use the "Set Transparent" button) to make the background transparent, allowing the text to overlay other content (like a live video feed on a mac).
*   **Window Width / Height**: Manually set the resolution of the display window. Quick presets are available for common screens (720p, 1080p, etc.).
*   **Window X / Y Position**: Controls exactly where the window opens on your desktop. Useful for ensuring it always opens on the correct secondary monitor.
*   **Always On Top**: If checked, the translation window will stay floating above all other open windows.
*   **Lines to Keep Visible**: Controls how many previous translation segments remain on screen. Setting this to `1` shows only the current sentence. Increasing it shows a running history.
*   **Seconds Before Clearing**: How long the text remains on screen after the speaker stops talking.
    *   *Usage:* Increase this if people need more time to read. Decrease it if you want the screen to clear quickly for a cleaner look.
*   **Horizontal / Vertical Alignment**: Controls where the text appears within the window (e.g., Centered, Top-Left, Bottom-Middle).

---

## 3. Performance Optimization & VAD Settings
These are advanced settings to tune how the AI "hears" and processes speech. Adjusting these can help reduce latency (delay) or improve accuracy.

### Timing & Overlap
*   **Audio Block Duration (ms)**
    *   *Range:* 10ms - 50ms
    *   *Effect:* Controls how small the chunks of audio are that get processed.
    *   *Tuning:* Lower values (10-20ms) reduce latency (faster response) but force the CPU to work harder. Higher values are easier on the computer but add slight delay.

*   **Overlap After Processing (ms)**
    *   *Range:* 200ms - 1000ms
    *   *Effect:* When the system processes audio, it keeps a small "tail" of the previous audio to mix with the next chunk. This ensures that words spoken right at the cut-off point don't get chopped in half.
    *   *Tuning:* Increase this if you hear "clipped" words at the start of sentences.

*   **Min Silence To Finalize (ms)**
    *   *Range:* 300ms - 1200ms
    *   *Effect:* How long the speaker must pause before the system decides "The sentence is finished, send it to be translated."
    *   *Tuning:* Lower values make translations appear faster but might break sentences in the middle. Higher values wait for complete thoughts but appear slower.

*   **Min Speech To Start (ms)**
    *   *Range:* 800ms - 2000ms
    *   *Effect:* The minimum duration of sound required to trigger a translation event.
    *   *Tuning:* Helps filter out coughs, mic bumps, or short "um" sounds. Increase this if the system keeps trying to translate random noises.

*   **Max Utterance Duration (s)**
    *   *Range:* 6s - 20s
    *   *Effect:* A hard limit on how long the system will listen before *forcing* a translation, even if the speaker hasn't paused.
    *   *Tuning:* Prevents the system from getting stuck waiting endlessly if a speaker talks very fast without breathing.

### VAD (Voice Activity Detection) Settings
*   **Whisper No-speech Threshold**
    *   *Range:* 0.4 - 1.2
    *   *Effect:* Controls how strict the AI is about what counts as "speech."
    *   *Tuning:* Higher values (0.8+) are stricter and will ignore background noise better, but might miss quiet whispering. Lower values hear everything but might hallucinate text from noise.

*   **Enable Whisper VAD Filter**
    *   *Effect:* Uses an internal filter within the Whisper model to ignore non-speech segments.
    *   *Recommendation:* Enable this generally. Disable it only if you find the system is ignoring soft or distant speech.

---

## 4. CPU Performance Controls
These settings help manage your computer's resources.

*   **CPU Threads**
    *   *Effect:* How many CPU cores are dedicated to the mathematics of transcription.
    *   *Tuning:* Lower this if your computer feels sluggish or unresponsive while running the translator. Increase it (up to your physical core count) for faster transcription.

*   **Audio Batch Size**
    *   *Effect:* Processes multiple audio chunks at once.
    *   *Tuning:* Higher values are more efficient (less CPU heat) but add latency because the system waits to fill the batch. Keep at `1` for real-time usage.

*   **Parallel Translation Workers**
    *   *Effect:* How many translation requests can happen at the same time.
    *   *Tuning:* If you have a fast computer, increasing this ensures that rapid-fire sentences don't get backed up in a queue.

*   **Audio Buffer Duration (s)**
    *   *Effect:* The maximum amount of audio history kept in memory.
    *   *Tuning:* Longer buffers provide more context for the AI but use more RAM. 20-30 seconds is usually sufficient.

*   **Speech Energy Threshold**
    *   *Effect:* A basic volume gate. Sounds quieter than this level are ignored completely.
    *   *Tuning:* Increase this if you are in a noisy room or have a noisy microphone. Decrease it for sensitive studio microphones.

---

## 5. Whisper Model Settings
These settings control the "brain" of the transcription engine.

*   **Whisper Model Size**
    *   *Choices:* tiny, base, small, medium, large-v2, large-v3
    *   *Effect:* Controls the size and intelligence of the transcription model.
    *   *Trade-off:* Larger models (medium, large) are much more accurate but require significantly more CPU/RAM and run slower. Smaller models (tiny, base) are instant but may make mistakes. **"Small" or "Base" is recommended for most real-time uses.**

*   **Compute Device**
    *   *Choices:* CPU Only, CUDA GPU (NVIDIA), Metal GPU (Apple)
    *   *Effect:* Determines what hardware runs the AI.
    *   *Recommendation:* Always use **GPU** if you have one available, as it is vastly faster. Use **CPU Only** if the application is crashing or unstable.

*   **Compute Precision**
    *   *Choices:* int8, float16, float32
    *   *Effect:* Controls the mathematical precision of the AI.
    *   *Recommendation:* **int8** is the fastest and uses the least memory with negligible quality loss. Use **float16** or **float32** only if you need absolute maximum accuracy and have powerful hardware.


---

## 6. Audio-Text Synchronization
These settings help sync the "mouth" (audio) with the "subtitles" (text).

*   **Text Display Delay (s)**
    *   *Effect:* Delays the appearance of text on the screen.
    *   *Usage:* Use this if the text is appearing *too* fast, before the audio has finished playing.

*   **Audio Output Delay (s)**
    *   *Effect:* Delays the playback of the spoken translation.
    *   *Usage:* Use this if you want the text to appear first so people can read it before they hear it.

---

## 7. Translation History
*   **View Translation Logs**: Click the "Refresh Logs" button to see a text record of everything translated in the current session. This is useful for reviewing the sermon or checking for translation errors after the fact.
