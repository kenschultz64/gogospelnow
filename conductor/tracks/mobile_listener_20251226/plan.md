# Plan: Implement Mobile Listener App

## Phase 1: Backend Integration [checkpoint: dc64c42]
- [x] Task: Create FastAPI endpoints in main.py to serve listener.html and static assets b0beb16
- [x] Task: Implement a data polling/stream endpoint (e.g., /api/listener/status) to return current text and audio URL 90d0326
- [x] Task: Modify translator_core.py to buffer or expose the latest TTS audio for the listener client 913ae4e
- [~] Task: Create unit tests for the new listener endpoints
- [ ] Task: Conductor - User Manual Verification 'Backend Integration' (Protocol in workflow.md)

## Phase 2: Frontend Refinement [checkpoint: 9e5fbb8]
- [x] Task: Refactor listener.html to remove auto-pause on visibility change 3f97a4a
- [x] Task: Implement robust audio playback logic (e.g., audio queueing, NoSleep.js or Wake Lock) 3f97a4a
- [x] Task: Style listener.html to match the desired look (already provided) 3f97a4a
- [ ] Task: Conductor - User Manual Verification 'Frontend Refinement' (Protocol in workflow.md)

## Phase 3: Performance & Audio
- [ ] Task: Optimize audio delivery (ensure small, playable chunks)
- [ ] Task: Verify background playback on actual mobile devices (simulated or user test)
- [ ] Task: Conductor - User Manual Verification 'Performance & Audio' (Protocol in workflow.md)
