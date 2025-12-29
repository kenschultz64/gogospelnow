# GoGospelNow - Frequently Asked Questions

## Cost & Licensing

### Is the software free to use?

**Yes! GoGospelNow is open source and completely free to use.**

| Component | Cost |
|-----------|------|
| **Software** | Free (open source) |
| **Local models** (Ollama, Whisper, Kokoro) | Free |
| **Cloud APIs** (optional) | Pay-per-use (minimal) |
| **Installation help** (optional) | $75/hour |

### What are the ongoing costs?

**Fully Offline (Local Models): $0/month**

If you use local models for transcription (Whisper), translation (Ollama), and TTS (Kokoro), there are **no ongoing costs**. Everything runs on your computer.

**With Cloud APIs: Minimal costs**

If you use cloud APIs for better accuracy or more languages:

| Service | Typical Monthly Cost | Notes |
|---------|---------------------|-------|
| **Google Cloud TTS** | $0-5/month | Free tier covers most churches (1 service/week) |
| **Groq API** | $0.01-0.10/month | Extremely affordable |
| **OpenAI/Mistral API** | $0.05-0.50/month | Slightly more expensive |

### API Cost Example (Groq - Recommended)

Groq offers **fast inference at very low cost**. For translation, you don't need expensive "thinking" models.

**Example with Llama 3.3 70B or Mistral 8B:**

| Metric | Estimate |
|--------|----------|
| Tokens per translation | ~100-200 |
| Translations per 1-hour sermon | ~150-300 |
| Total tokens per sermon | ~30,000-60,000 |
| **Cost per sermon** | **~$0.002-0.005** |
| **Cost per month (4 services)** | **~$0.01-0.02** |

That's **less than 2 cents per month** for a typical church!

### Why are cloud APIs so cheap for translation?

- Translation uses **small prompts** (just a sentence at a time)
- You don't need "reasoning" or "thinking" models
- Output is short (just the translated text)
- Modern APIs charge fractions of a cent per 1000 tokens

**Bottom line:** For most churches using cloud APIs, the cost is essentially negligible - less than the cost of a pack of gum per month.

---

### Can I translate to multiple languages at the same time?

**Yes!** You can run multiple translations simultaneously during the same service.

**Recommended Setup:**

For best results, use a separate computer for each language:

| Languages | Setup | Investment |
|-----------|-------|------------|
| **1 language** | 1 computer | Your existing PC/laptop |
| **2 languages** | 2 computers | + $300-500 (mini PC) |
| **3 languages** | 3 computers | + $600-1000 (2 mini PCs) |

**Why separate computers?**
- Each translation stream needs its own processing power
- Prevents audio conflicts
- More reliable than running multiple instances
- Easy to manage - one person per language

**Recommended Hardware:**

| Option | Price Range | Notes |
|--------|-------------|-------|
| **Mac Mini M4** | $599+ | ⭐ Excellent choice! Unified memory acts as GPU. Great performance. |
| **Ryzen 7/9 + 32GB RAM** | $600-900 | Matches Mac Mini performance with enough memory |
| **AMD Ryzen 5 mini PC** | $300-400 | Good mid-range option |
| **Intel N95/N100 mini PC** | $150-200 | Budget option (use with cloud APIs) |

**Operating System Tips:**
- **Mac Mini M4**: macOS works great out of the box
- **Windows with NVIDIA GPU**: Best for local Whisper acceleration
- **Linux**: Recommended for any computer **without** a GPU - better performance than Windows for CPU-only processing

**Performance Notes:**
- Mac Mini M4's unified memory architecture provides excellent AI performance without a separate GPU
- Ryzen 7 or 9 with 32GB+ RAM can match Mac Mini performance
- Budget mini PCs work well when using cloud APIs (offloads heavy processing)

**All computers share:**
- Same microphone input (via audio splitter or mixer)
- Same network (each serves different phones)
- Same listener app (users just connect to their language's IP)

**The cost to add new languages is very low** - a $300-500 mini PC can handle a full language, and all the software is free!

---

## Mobile Listener App

### How much battery does the listener app use?

The app is designed to be lightweight. Estimated battery usage per hour:

| Component | Drain/Hour |
|-----------|-----------|
| Screen on | 15-25% |
| WiFi + Audio | 3-5% |
| App activity | 1-2% |
| **Total** | **~20-35%** |

**Recommendation:** Arrive with 50%+ battery for a 1-hour service, or 70%+ for longer services.

**Tips to extend battery:**
- Lower screen brightness
- Use wired earbuds (uses less than Bluetooth)
- Close other apps
- Enable Low Power Mode

---

### Can the app handle a 2-hour service?

Yes! Starting at 70-80% battery, most phones can easily handle a 2-hour service. The app uses minimal resources - it only polls for text updates and plays audio.

---

### Why is there a 1-second delay before audio plays?

The app checks the server for updates every 1 second. This is the optimal balance between:
- Responsiveness (near real-time updates)
- Battery life (not constantly polling)
- Network efficiency (handles many phones)

A 1-second delay is not noticeable during normal sermon translation.

---

### How many phones can connect at once?

| Congregation Size | Network Needed |
|-------------------|----------------|
| Up to 50 phones | Standard WiFi router |
| 50-150 phones | Dual-band router or 2 access points |
| 150-300 phones | Business-grade WiFi |
| 300+ phones | Multiple access points |

Each phone uses only ~30-50 kbps of bandwidth - very light.

---

### Does the listener app work with NDI video on the same network?

Yes! The listener app uses minimal bandwidth (~50 kbps per phone). Even with multiple NDI video feeds (100+ Mbps each), a gigabit network handles both without issues.

---

### Why does my Android screen turn off during long services?

Use the **native Android app** instead of the web page. The Android app uses a native wake lock that keeps the screen on indefinitely, regardless of system timeout settings.

Download the APK from your church's website.

---

### Why does my iPhone screen turn off?

The iOS web app includes a silent video loop that keeps the screen on. However, if it still turns off:

1. Go to **Settings → Display & Brightness → Auto-Lock**
2. Set to **Never** (temporarily)
3. Remember to change it back after the service

---

### Can I use Bluetooth earbuds?

Yes! Both wired and Bluetooth earbuds work fine. Bluetooth adds about 3-5% extra battery drain per hour, which is manageable.

---

### Do phones need internet access?

**No!** Phones only need to connect to the same WiFi network as the translator computer. The WiFi router does NOT need an internet connection. This is perfect for:
- Mission trips without internet
- Remote locations
- Buildings with poor connectivity

---

### How many languages are supported?

| Mode | Translation Languages | TTS Voices |
|------|----------------------|------------|
| **With Internet** (APIs) | 100+ languages | 50+ languages |
| **Offline** (Local models) | 20-30 common languages | 8 languages |

**With Internet (Cloud APIs):**
- **Groq API**: Supports major world languages
- **Google Translate**: 100+ languages
- **Google Cloud TTS**: 50+ languages with neural voices

**Offline (Local Models):**
- **Ollama translation**: Works best with common languages (Spanish, French, German, Chinese, Japanese, Korean, Portuguese, Italian, Russian, Arabic, Hindi, etc.)
- **Kokoro TTS**: English, Spanish, French, German, Italian, Portuguese, Japanese, Chinese

For the complete list of TTS voices, see **[TTS Supported Languages](TTS_SUPPORTED_LANGUAGES.md)**.

**Tip:** For less common languages, use cloud APIs for best results.

---

### How accurate is the translation?

**It depends on the models used, but results are very good.**

With the base Whisper model for transcription and a small local model like `gemma3n:e2b` for translation, we're seeing approximately **90% accuracy** when analyzing translation logs.

**What translates well:**
- ✅ Core sermon content and theology
- ✅ Biblical references and quotes
- ✅ Everyday vocabulary and phrases
- ✅ Most grammatical structures

**What may not translate perfectly:**
- ⚠️ Pop culture references and idioms
- ⚠️ Local slang or colloquialisms  
- ⚠️ Jokes that rely on wordplay
- ⚠️ Very technical or specialized terminology

**Compared to human translators:**

In many cases, AI translation may be **more consistent** than volunteer human translators in churches and on the mission field. Key advantages:
- Never gets tired or loses focus
- Consistent terminology throughout
- No personal interpretation bias
- Available for any language combination

**Verification:**

Unlike human translators where accuracy is hard to verify without recordings, AI translation creates logs that can be reviewed. You can run the translation logs through another AI after the fact to check accuracy.

**Tips for best results:**
- Some languages are supported better than others - experiment with different models
- Models produced in Asia (like some Alibaba models) may perform better with Asian languages
- Larger models generally produce more accurate translations
- Cloud APIs (Groq, Google) often outperform small local models for accuracy

**Reverse Translation ("Universal Translator"):**
258: You can also use the system in **reverse** to translate from any of the ~86 supported source languages back into English.
259: - **Input:** Any supported language (e.g., Urdu, Korean, Somali)
260: - **Output:** English (Text & Audio)
261: - This effectively allows an English speaker to understand sermons or speeches in nearly any major world language.
262: 
263: ---

## Server / Translator

### Is the program hard to use?

**No, but initial setup requires some technical knowledge.**

| Phase | Difficulty | Time |
|-------|-----------|------|
| **Installation** | Moderate | 30-60 min first time |
| **Configuration** | Moderate | 15-30 min to optimize |
| **Daily use** | Easy | Just click Start! |

**Initial Setup (one-time):**
- Installing Python, Docker, and Ollama requires following instructions carefully
- Configuring the right model for your language pair may take some experimentation
- Adjusting speech speed and audio settings for your hardware

**Once configured:**
- Starting translation is one click
- Changing languages is a dropdown menu
- Stopping is one click
- Settings are saved between sessions

**Who should set it up?**
- Someone comfortable with installing software
- Doesn't require programming knowledge
- Follow the README step-by-step

**Daily operators don't need technical skills** - once it's set up, anyone can run it.

**Need help with installation?**

If your church doesn't have someone with the technical expertise, we offer remote installation support:

| Service | Price | Description |
|---------|-------|-------------|
| **Installation Consultation** | $75/hour | Remote setup via screen share |

We'll help you:
- Install all required software
- Configure models for your language pair
- Optimize settings for your hardware
- Test the system end-to-end

Contact us at [GoGospelNow.com](https://gogospelnow.com) to schedule.

---

### What operating systems are supported?

The translator server runs on:
- ✅ Windows 10/11
- ✅ macOS (Intel and Apple Silicon)
- ✅ Linux (Ubuntu, Debian, etc.)

---

### Can the system run completely offline?

Yes! Using local models:
- **Whisper** for transcription (local)
- **Ollama** for translation (local)
- **Kokoro** for text-to-speech (local)

No internet connection is required. All processing happens on the local computer.

---

### How much computer power do I need?

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB+ |
| GPU | None (CPU works) | NVIDIA GPU for faster Whisper |
| Storage | 10 GB free | SSD preferred |

The translator works on most modern laptops and desktops.

---

### Can I run this on a Raspberry Pi?

**It depends on your setup:**

| Setup | Raspberry Pi 5 (8GB) | Older Pi Models |
|-------|---------------------|-----------------|
| **With cloud APIs** (Groq, Google) | ✅ Works | ⚠️ May work |
| **With local models** (Ollama, Whisper) | ❌ Too slow | ❌ No |

**Raspberry Pi 5 (8GB) can work** if you use:
- Cloud API for transcription (e.g., Groq Whisper)
- Cloud API for translation (e.g., Groq, Google Translate)
- Kokoro for TTS (lightweight enough for Pi 5)

This requires internet access but offloads the heavy processing to cloud servers.

**For fully offline/local operation**, a laptop or desktop with 16GB+ RAM is recommended.

---

## Audio Setup

### How do I prevent audio feedback loops?

The translated audio should NOT be picked up by the input microphone. Options:
1. Use a separate aux send for the translator input
2. Use headphones/earbuds for translated audio output
3. Keep the translator audio isolated from the main sound system

---

### Can I use the computer's built-in microphone?

Yes, but for best results use:
- A dedicated USB microphone
- A direct audio feed from the sound board
- A wireless microphone receiver

---

## Troubleshooting

### The phone can't connect to the server

1. Make sure both devices are on the **same WiFi network**
2. Check the server IP address is correct (shown in the app header)
3. Use port **8000** (not 7860)
4. Check Windows Firewall isn't blocking the connection

---

### Audio won't play on my phone

1. Make sure your phone's volume is up
2. Check that the phone isn't in silent/vibrate mode
3. On iOS: Tap the ▶ play button to unlock audio
4. Try disconnecting and reconnecting

---

### The translation seems slow

1. Check your computer's CPU usage
2. Consider using a faster translation model
3. Use a GPU if available for Whisper
4. Reduce the Whisper model size (e.g., use "base" instead of "large")

---

*Have a question not answered here? Open an issue on GitHub or contact support.*
