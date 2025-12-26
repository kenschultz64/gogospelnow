# Security Setup Guide

## Google Cloud API Key Configuration

This application requires a Google Cloud API key for Google Text-to-Speech functionality. Follow these steps to configure it securely.

### ⚠️ IMPORTANT: Your API Key Was Exposed

If you previously committed `settings.json` to Git, your API key may be exposed in your repository history. You should:

1. **Revoke the exposed API key immediately** at [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. **Generate a new API key**
3. **Follow the secure setup methods below**

---

## Recommended Setup Methods

### Method 1: Environment Variable (Most Secure) ✅

This is the **recommended approach** for security.

#### On macOS/Linux:

1. **Temporary (current session only):**
   ```bash
   export GOOGLE_API_KEY="your-new-api-key-here"
   python main.py
   ```

2. **Permanent (add to shell profile):**
   ```bash
   # For zsh (macOS default)
   echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.zshrc
   source ~/.zshrc
   
   # For bash
   echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Launch the app:**
   ```bash
   python main.py
   ```

#### On Windows:

1. **Temporary (current session only):**
   ```powershell
   $env:GOOGLE_API_KEY="your-new-api-key-here"
   python main.py
   ```

2. **Permanent (system environment variable):**
   - Open System Properties → Environment Variables
   - Add new User Variable:
     - Name: `GOOGLE_API_KEY`
     - Value: `your-api-key-here`
   - Restart your terminal/IDE

---

### Method 2: UI Entry (User-Friendly)

For end users who prefer a graphical interface:

1. Launch the application: `python main.py`
2. Navigate to the **Settings** tab
3. Enter your API key in the "Google Cloud API Key" field (it will be masked)
4. Click **"Save Server Settings"** (orange button)
5. The key is saved to `settings.json` (which is now gitignored)

**Note:** The UI will show a status indicator:
- ✅ Green = Using environment variable (most secure)
- ⚠️ Yellow = Using settings.json (less secure but acceptable)
- ❌ Red = No API key configured

---

### Method 3: Manual Configuration

For advanced users:

1. Create or edit `settings.json` in the project root:
   ```json
   {
       "translation_server": "http://localhost:11434",
       "tts_server_url": "http://localhost:8880/v1",
       "google_api_key": "your-new-api-key-here"
   }
   ```

2. This file is now in `.gitignore` and won't be committed

---

## Priority Order

The application checks for the API key in this order:

1. **Environment variable** `GOOGLE_API_KEY` (highest priority)
2. **settings.json** file (fallback)
3. **None** (error message shown)

---

## Additional Security Best Practices

### 1. Restrict Your API Key

In [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

- **Application restrictions:** Set to "IP addresses" and add your server IP
- **API restrictions:** Limit to "Cloud Text-to-Speech API" only
- **Set usage quotas** to prevent unexpected charges

### 2. Monitor Usage

- Regularly check your [Google Cloud billing](https://console.cloud.google.com/billing)
- Set up billing alerts
- Review API usage in the [APIs & Services dashboard](https://console.cloud.google.com/apis/dashboard)

### 3. Rotate Keys Regularly

- Generate new API keys every 90 days
- Delete old/unused keys immediately

### 4. Never Commit Sensitive Files

The following files are now in `.gitignore`:
- `settings.json`
- `user_preferences.json`
- `*.backup*` files

If you accidentally commit them:
```bash
# Remove from Git history (use with caution)
git rm --cached settings.json
git commit -m "Remove sensitive files"
```

---

## Troubleshooting

### "No API key provided" Error

1. Check if environment variable is set:
   ```bash
   echo $GOOGLE_API_KEY  # macOS/Linux
   echo %GOOGLE_API_KEY%  # Windows CMD
   echo $env:GOOGLE_API_KEY  # Windows PowerShell
   ```

2. Check `settings.json` exists and contains the key

3. Restart the application after setting environment variables

### Environment Variable Not Working

- Make sure you've restarted your terminal/IDE after setting it
- Check for typos in the variable name (must be exactly `GOOGLE_API_KEY`)
- Verify the key is valid in Google Cloud Console

---

## Getting a Google Cloud API Key

If you don't have an API key yet:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Cloud Text-to-Speech API**
4. Go to **APIs & Services → Credentials**
5. Click **"Create Credentials" → "API Key"**
6. Copy the key and follow the setup methods above
7. **Immediately restrict the key** as described in "Additional Security Best Practices"

---

## Questions?

If you have security concerns or questions, please open an issue on the project repository.
