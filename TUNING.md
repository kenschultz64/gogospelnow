# Performance Tuning Guide

This guide helps you tune latency, stability, and quality for the Real‑Time Preaching Translator.

## What to tune (high impact)
- **Compute device & precision** (`user_preferences.json` / Settings UI)
  - CPU Only + int8 (fastest on low-end CPU)
  - CUDA/Metal + float16 (balanced on GPU)
  - CUDA/Metal + float32 (highest quality, more VRAM)
- **Model choice (Ollama)**
  - Smaller, quantized models = lower latency (e.g., `llama3.2:3b-instruct-q4_K_M`, `gemma3n:e2b`)
  - Larger models = better translation quality but slower
- **Audio pipeline timing** (Settings UI)
  - Text Display Delay (−2.0s to +5.0s)
  - Audio Output Delay (0.0s to +3.0s)
  - Synchronization Mode: Real‑time, Sentence Complete, Manual
- **Runtime block sizes** (lower latency vs CPU cost)
  - `block_duration_ms` - Audio block size in milliseconds
  - `overlap_s` - Overlap after processing in seconds
  - `min_silence_s` - Minimum silence to finalize in seconds
  - `min_speech_s` - Minimum speech to start in seconds
  - `max_speech_s` - Maximum utterance duration in seconds

## Quick recipes

### 1) CPU‑only (lowest latency on modest hardware)
- Device: CPU Only
- Precision: int8
- Model: `gemma3n:e2b` or `llama3.2:3b-instruct-q4_K_M`
- Runtime:
  - block_duration_ms: 50
  - overlap_s: 0.6 (600ms)
  - min_silence_s: 0.8 (800ms)
  - min_speech_s: 1.2 (1200ms)
  - max_speech_s: 8.0
- Sync: Text Display Delay 0.2s, Audio Output Delay 0.2s

### 2) Balanced GPU (good quality + responsive)
- Device: CUDA/Metal
- Precision: float16
- Model: `gemma3n:e4b` or `gemma3:4b`
- Runtime:
  - block_duration_ms: 30
  - overlap_s: 0.5 (500ms)
  - min_silence_s: 0.7 (700ms)
  - min_speech_s: 1.0 (1000ms)
  - max_speech_s: 10.0
- Sync: Text Display Delay 0.1s, Audio Output Delay 0.1s

### 3) Quality focus (best translation quality)
- Device: CUDA/Metal
- Precision: float32 (only if VRAM allows) or float16
- Model: `gemma3:4b` (or try larger if your hardware allows)
- Runtime:
  - block_duration_ms: 20
  - overlap_s: 0.45 (450ms)
  - min_silence_s: 0.6 (600ms)
  - min_speech_s: 1.0 (1000ms)
  - max_speech_s: 12.0
- Sync: Text Display Delay 0.0s, Audio Output Delay 0.0–0.1s

## Whisper and VAD tips
- If soft speech is getting dropped, lower Whisper no‑speech threshold or disable Whisper VAD filter.
- Very noisy rooms: increase min_speech_s and min_silence_s slightly.

## Measuring and reducing latency
- Watch the UI’s transcript timing versus audio playback.
- Reduce model size/precision or switch to GPU to cut translation latency.
- Increase `block_duration_ms` on weak CPUs to reduce CPU spikes.
- Close other heavy apps; set CPU thread env vars (already set in `main.py`).

## Audio device stability
- On Windows/macOS, ensure the selected input/output devices match system settings.
- If playback glitches, try a small Audio Output Delay (0.1–0.3s).

## Model selection guidance
- Start small and step up:
  1. `gemma3n:e2b` (very fast)
  2. `llama3.2:3b-instruct-q4_K_M` (balanced CPU)
  3. `gemma3n:e4b` / `gemma3:4b` (better quality)
- Use `ollama list` to see what’s available; pull models as needed.

## Where these map in code
- Runtime defaults: see `main.py` → `RUNTIME_PARAMS` (lines 122-128)
- Device/precision, server URLs, and UI options: see `translator_core.py` and `user_preferences.json`
- Current defaults:
  - block_duration_ms: 30
  - overlap_s: 0.4 (400ms)
  - min_silence_s: 0.6 (600ms)
  - min_speech_s: 1.2 (1200ms)
  - max_speech_s: 8.0

## Troubleshooting quick checks
- High latency: smaller model, GPU, or int8; increase block_duration_ms.
- Clipped words: increase overlap_s (e.g., +0.1s).
- Desync: adjust Text Display Delay or Audio Output Delay by ±0.1–0.3s.
- No TTS: ensure Kokoro API at `http://localhost:8880` and correct voice, or Google Cloud API key is set if using Google voices.
