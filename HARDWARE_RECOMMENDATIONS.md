# Hardware-Specific Recommended Settings

Use this guide to configure **GoGospelNow** for your specific computer hardware.

---

## 1. Mac Mini (M4 Chip, 16GB Unified Memory)
**Profile:** High-Efficiency ARM
The M4 chip is incredibly fast for AI tasks, but with 16GB of shared memory, we need to balance the memory usage between the operating system, the Translation model (Ollama), and the Whisper transcription model.

*   **Whisper Model Size:** `small` (Recommended) or `medium`
    *   *Reason:* `small` is lightning fast on Apple Silicon. `medium` is possible but might compete for RAM if you run large translation models.
*   **Compute Device:** `Metal GPU (Apple)`
*   **Compute Precision:** `float16`
    *   *Reason:* Apple Silicon is optimized for fp16 operations.

*   **CPU Threads:** `4`
    *   *Reason:* Leave remaining cores for the OS and background tasks.
*   **Parallel Translation Workers:** `4`

---

## 2. PC with Ryzen 9 (64GB RAM)
**Profile:** High-End CPU Powerhouse
With 64GB of RAM, memory is not an issue. However, without a dedicated NVIDIA GPU, raw transcription speed is limited by the CPU. The Ryzen 9 has many cores, so we can throw more threads at the problem.

*   **Whisper Model Size:** `small` (Recommended) or `medium`
    *   *Reason:* Real-time transcription on CPU (even a Ryzen 9) can struggle with `large` models. `small` offers the best balance of speed vs. accuracy for CPU inference.
*   **Compute Device:** `CPU Only`
*   **Compute Precision:** `int8`
    *   *Reason:* **Critical.** `int8` quantization significantly speeds up CPU inference.

*   **CPU Threads:** `10`
    *   *Reason:* Utilizing more of the Ryzen 9's high core count.
*   **Parallel Translation Workers:** `6`

---

## 3. PC with Intel Core i7 (32GB RAM)
**Profile:** Standard High-Performance CPU
A capable machine, but CPU-based transcription requires careful tuning to maintain low latency.

*   **Whisper Model Size:** `small` (Safe) or `base` (Fastest)
    *   *Reason:* Start with `small`. If you notice the text lagging behind the audio, switch to `base`.
*   **Compute Device:** `CPU Only`
*   **Compute Precision:** `int8`
    *   *Reason:* Essential for keeping latency low on Intel CPUs.

*   **CPU Threads:** `6`
*   **Parallel Translation Workers:** `2`

---

## 4. PC with Ryzen 7 (32GB RAM) + NVIDIA RTX 3090 (24GB VRAM)
**Profile:** AI Powerhouse (The "Pro" Setup)
The RTX 3090 is a beast for AI. This machine can run the highest quality models with the lowest latency.

*   **Whisper Model Size:** `large-v3`
    *   *Reason:* The 3090 has 24GB of VRAM, which can easily swallow the largest Whisper model for maximum accuracy.
*   **Compute Device:** `CUDA GPU`
*   **Compute Precision:** `float16`
    *   *Reason:* Native precision for NVIDIA GPUs; runs extremely fast.

*   **CPU Threads:** `4`
    *   *Reason:* The GPU is doing the heavy lifting; the CPU just feeds it data.
*   **Parallel Translation Workers:** `8`
    *   *Reason:* You can process many sentences simultaneously without slowing down.

---

## Summary Table

| Setting | Mac M4 (16GB) | Ryzen 9 (64GB) | Intel i7 (32GB) | Ryzen 7 + RTX 3090 |
| :--- | :--- | :--- | :--- | :--- |
| **Whisper Model** | `small` | `small` | `small` / `base` | `large-v3` |
| **Device** | `Metal GPU` | `CPU Only` | `CPU Only` | `CUDA GPU` |
| **Precision** | `float16` | `int8` | `int8` | `float16` |
| **CPU Threads** | `4` | `10` | `6` | `4` |
