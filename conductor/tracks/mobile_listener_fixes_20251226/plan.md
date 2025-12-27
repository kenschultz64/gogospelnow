# Plan: Fix Mobile Listener Screen Awake and Audio Controls

## Phase 1: Security & Separation
- [x] Task: Create a separate FastAPI app for the Listener (port 8000) dbd0825
- [x] Task: Update main.py to run the Listener app in a separate thread/process dbd0825
- [x] Task: Ensure cross-origin resource sharing (CORS) or shared state allows Listener to get data dbd0825
- [ ] Task: Conductor - User Manual Verification 'Security & Separation' (Protocol in workflow.md)

## Phase 2: Screen Awake Fixes
- [ ] Task: Integrate NoSleep.js library (or equivalent robust implementation)
- [ ] Task: Ensure video element is properly configured (playsinline, hidden but active)
- [ ] Task: Conductor - User Manual Verification 'Screen Awake' (Protocol in workflow.md)

## Phase 3: Audio Controls
- [ ] Task: Implement a custom sticky footer audio player (Play/Pause, Status)
- [ ] Task: Ensure controls connect to the existing audio queue logic
- [ ] Task: Conductor - User Manual Verification 'Audio Controls' (Protocol in workflow.md)
