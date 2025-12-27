# Spec: Fix Mobile Listener Screen Awake and Audio Controls

## Overview
Resolve the issue where the mobile device screen times out during playback. Implement persistent audio controls. Crucially, separate the Listener App onto a different port to secure the main admin interface from congregation access.

## Goals
- **Separate Port:** Serve the Listener App on a dedicated port (e.g., 8000) to isolate it from the Gradio admin UI (7860).
- **Force Screen Awake:** Implement a robust solution for keeping the screen on.
- **Persistent Audio Controls:** Add a custom audio control interface (sticky footer).

## Acceptance Criteria
- Listener App is accessible on `http://<server-ip>:8000` (or similar) and NOT on 7860.
- Admin UI on 7860 is NOT accessible from port 8000.
- Screen remains on indefinitely while "Listening".
- Audio controls are available to restart playback.
