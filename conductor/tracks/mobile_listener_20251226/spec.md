# Spec: Implement Mobile Listener App

## Overview
Implement a mobile-friendly web interface (\listener.html\) served by the main application that allows users to view real-time translations and listen to TTS audio via their mobile devices. The app must ensure audio playback continues even when the device screen times out or is locked.

## Goals
- Serve \listener.html\ from the main application server.
- Implement backend endpoints to provide real-time transcription, translation, and audio data.
- Fix client-side logic to prevent audio interruption during screen timeout (remove visibility pause logic, enhance Wake Lock).
- Ensure minimal impact on main server performance.

## Acceptance Criteria
- Users can access the listener app via a URL (e.g., \http://<server-ip>:7860/listener\).
- Transcription and translation text update in real-time.
- Audio plays continuously even when the phone screen is turned off.
- The solution works on both iOS and Android browsers.
- Main translation loop performance is not degraded.