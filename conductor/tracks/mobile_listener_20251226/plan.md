# Plan: Implement Mobile Listener App

## Phase 1: Backend Integration
- [x] Task: Create FastAPI endpoints in main.py to serve listener.html and static assets b0beb16
- [ ] Task: Implement a data polling/stream endpoint (e.g., \/api/listener/status\) to return current text and audio URL
- [ ] Task: Modify 	ranslator_core.py to buffer or expose the latest TTS audio for the listener client
- [ ] Task: Create unit tests for the new listener endpoints
- [ ] Task: Conductor - User Manual Verification 'Backend Integration' (Protocol in workflow.md)

## Phase 2: Frontend Refinement
- [ ] Task: Refactor \listener.html\ to remove auto-pause on visibility change
- [ ] Task: Implement robust audio playback logic (e.g., audio queueing, NoSleep.js or Wake Lock)
- [ ] Task: Style \listener.html\ to match the desired look (already provided)
- [ ] Task: Conductor - User Manual Verification 'Frontend Refinement' (Protocol in workflow.md)

## Phase 3: Performance & Audio
- [ ] Task: Optimize audio delivery (ensure small, playable chunks)
- [ ] Task: Verify background playback on actual mobile devices (simulated or user test)
- [ ] Task: Conductor - User Manual Verification 'Performance & Audio' (Protocol in workflow.md)
