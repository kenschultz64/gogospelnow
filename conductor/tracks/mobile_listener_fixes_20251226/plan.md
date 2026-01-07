# Plan: Fix Mobile Listener Screen Awake and Audio Controls

## Phase 1: Security & Separation [checkpoint: b3a70ae]
- [x] Task: Create a separate FastAPI app for the Listener (port 8000) dbd0825
- [x] Task: Update main.py to run the Listener app in a separate thread/process dbd0825
- [x] Task: Ensure cross-origin resource sharing (CORS) or shared state allows Listener to get data dbd0825
- [x] Task: Conductor - User Manual Verification 'Security & Separation' (Protocol in workflow.md) (Verified by user)

## Phase 2: Screen Awake Fixes [checkpoint: 6856403]
- [x] Task: Integrate NoSleep.js library (or equivalent robust implementation) 2683996
- [x] Task: Ensure video element is properly configured (playsinline, hidden but active) 2683996
- [x] Task: Conductor - User Manual Verification 'Screen Awake' (Protocol in workflow.md) (Verified by user)

## Phase 3: Audio Controls [checkpoint: d636053]
- [x] Task: Implement visible video loop for robust wake lock 5d2e2fa
- [x] Task: Implement a custom sticky footer audio player (Play/Pause, Status) 5d2e2fa
- [x] Task: Ensure controls connect to the existing audio queue logic 5d2e2fa
- [x] Task: Conductor - User Manual Verification 'Audio Controls' (Protocol in workflow.md) (Verified by user)
