# Plan: Graceful Shutdown & Universal Launcher

## Phase 1: Graceful Shutdown
- [x] Task: Add 'Shutdown' button to the Gradio interface
- [x] Task: Implement shutdown logic in `main.py` (signal handling, thread stopping)
- [x] Task: Ensure clean exit of `uvicorn` and `gradio`
- [ ] Task: Conductor - User Manual Verification 'Graceful Shutdown' (Protocol in workflow.md)

## Phase 2: Universal Launcher Installer
- [x] Task: Create `install_launcher.py` script structure
- [x] Task: Implement Windows shortcut generation (VBScript or similar to avoid heavy deps)
- [x] Task: Implement Linux `.desktop` file generation
- [x] Task: Implement macOS `.command` or `.app` generation
- [ ] Task: Conductor - User Manual Verification 'Universal Launcher' (Protocol in workflow.md)

## Phase 3: Verification & Documentation
- [x] Task: Verify shutdown functionality
- [ ] Task: Verify Linux launcher creation
- [x] Task: Update `README.md` with launcher installation instructions
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
