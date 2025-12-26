# Product Guidelines

## 1. Design Principles

- **Modern & Sleek Aesthetic:** The interface should leverage contemporary design trends, utilizing "dark mode" aesthetics and subtle animations to provide a professional, polished feel.
- **Instructional & Empathetic Tone:** Documentation and UI cues must focus on guiding non-technical users (e.g., church volunteers) through setup and operation with encouraging, clear language.
- **Audience-Centric Display:** The Secondary Output Monitor must be strictly distraction-free, using large, centered text and solid backgrounds to ensure the translated message is the sole focus for the congregation.

## 2. Technical & Operational Standards

- **Stability First:** Reliability of the core offline translation loop is the highest priority. New features or cloud integrations must not compromise the bulletproof performance required for live services.
- **Graceful Degradation:** The system must proactively manage "offline" states. If a cloud-based service (like Google TTS) is unavailable, the UI should clearly explain why and immediately offer the best local alternative (e.g., Kokoro) to maintain continuity.
- **Cross-Platform Consistency:** While the installation steps differ by OS, the core user experience and configuration should remain consistent across Windows, macOS, and Linux.

## 3. User Experience (UX)

- **One-Click Confidence:** Aim for a "launch and forget" experience. Once configured, starting the translation should require minimal interaction.
- **Visual Feedback:** Provide clear, modern visual indicators for transcription status, translation progress, and service health without overwhelming the user with technical logs.