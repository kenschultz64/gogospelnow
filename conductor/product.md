# Initial Concept

Real time transcription, translation and tts for live preaching situations on minimal hardware without internet. But also the flexiblityt to use internet or remote models for the function of transcription, translation, and tts output when necessary for speed or tts languages when new tts becomes availabe.

# Product Guide

## 1. Vision & Goals

**Vision:** To become the standard open-source tool for affordable multilingual church services globally, enabling any congregation to bridge language barriers regardless of their internet connectivity or budget.

**Core Goals:**
- **Minimal Latency:** Provide near-instant translation suitable for the dynamic pace of live preaching.
- **Hardware Efficiency:** Operate effectively on mid-range consumer hardware (e.g., standard laptops) without requiring expensive gaming rigs.
- **Offline Reliability:** Function completely without an internet connection once installed, ensuring stability in areas with poor infrastructure.
- **Hybrid Flexibility:** Allow users to seamlessly switch between local models and cloud-based services for transcription, translation, and TTS when connectivity and hardware allow, optimizing for speed or language support.

## 2. Target Audience

- **Primary:** Churches and ministries needing to provide simultaneous translation for multilingual congregations.
- **Secondary:** Missionaries and traveling evangelists operating in remote or low-connectivity environments.

## 3. Key Features

- **Real-Time Pipeline:** Integrated transcription (Faster-Whisper), translation (Ollama/LLMs), and Text-to-Speech (Kokoro/Google Cloud) optimized for low latency.
- **Hybrid Operation:**
    - **Offline Mode:** Uses local Docker containers for TTS and local LLMs for translation.
    - **Online Mode:** Optional integration with cloud APIs (OpenAI, Google, Groq, Mistral, Custom Endpoints) for enhanced performance or broader language support.
- **Hardware Optimization:** Tuned to run on non-gaming laptops while maintaining acceptable performance.
- **Cross-Platform Support:** Easy installation and operation on Windows, macOS, and Linux.

## 4. Constraints & Requirements

- **System:** Must be compatible with mid-range hardware (e.g., standard consumer laptops without dedicated GPUs).
- **Cross-Platform:** The solution must be installable and functional on major operating systems (Windows, macOS, Linux).
- **Connectivity:** The core "happy path" must assume zero internet connectivity during operation.