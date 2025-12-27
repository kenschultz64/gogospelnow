# Technology Stack

## Core Language & Runtime
- **Python (3.11+):** Primary programming language for the application logic and service orchestration.
- **Docker:** Used to containerize and run the Kokoro Text-to-Speech (TTS) engine, ensuring consistent performance across platforms.

## Artificial Intelligence & Machine Learning
- **Transcription:** \aster-whisper\ (utilizing CTranslate2) for high-performance, local speech-to-text.
- **Translation (Local):** \Ollama\ for running local Large Language Models (LLMs) like Gemma, Llama, and Granite.
- **Translation (Cloud):** Optional integration with \`OpenAI\`, \`Groq\`, \`xAI (Grok)\`, \`Mistral\`, and \`Custom OpenAI\` compatible endpoints.
- **Inference Engine:** \PyTorch\ (torch) for underlying ML computations.

## Audio & Signal Processing
- **Audio I/O:** \PyAudio\ and \sounddevice\ for low-latency microphone capture and speaker output.
- **Audio Analysis:** \librosa\ and \soundfile\ for waveform manipulation and processing.

## User Interface & Experience
- **Mobile Client:** Native HTML/JS web app (`listener.html`) served by FastAPI for low-latency mobile access.
- **Display Management:** \screeninfo\ for handling multi-monitor setups and the secondary output display.

## Infrastructure & Utilities
- **Networking:** \equests\ and \httpx\ for API communication with local (Ollama/Kokoro) and cloud providers.
- **Utilities:** \
umpy\ for efficient array operations on audio data.