# GoGospelNow Listener App

A native Android app for congregation members to receive real-time translations during church services.

## Features

- ✅ **Screen stays on** - Uses native Android FLAG_KEEP_SCREEN_ON (100% reliable)
- ✅ **Remembers server** - Enter IP once, app saves it for next time
- ✅ **Works for any church** - Each user enters their church's server IP
- ✅ **Audio playback** - Plays translated audio automatically
- ✅ **Beautiful dark UI** - Easy on the eyes during services

## Building the APK

### Prerequisites

1. **Android Studio** - Download from https://developer.android.com/studio
2. **Node.js** - Already installed if you set up this project

### Build Steps

1. **Open Android Studio**

2. **Open the Android project:**
   - File → Open
   - Navigate to `listener-app/android`
   - Click OK

3. **Wait for Gradle sync** (may take a few minutes the first time)

4. **Build the APK:**
   - Build → Build Bundle(s) / APK(s) → Build APK(s)
   - Or for a signed release: Build → Generate Signed Bundle / APK

5. **Find the APK:**
   - Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`
   - Release APK: `android/app/build/outputs/apk/release/app-release.apk`

### Quick Command Line Build (if you have Android SDK)

```bash
cd listener-app/android
./gradlew assembleDebug
```

The APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

## Distributing the APK

1. **Host on your website** - Upload the APK file
2. **Share the download link** - Users download and install directly
3. **Enable "Install from unknown sources"** - Android will prompt users for this

### Installation Instructions for Users

1. Download the APK from [your church website]
2. Tap the downloaded file
3. If prompted, tap "Settings" → Enable "Allow from this source"
4. Tap "Install"
5. Open "GoGospelNow Listener"
6. Enter your church's server address (shown on the translator computer)
7. Tap "Connect & Start Listening"

## Updating the App

After making changes to `www/index.html`:

```bash
cd listener-app
npx cap sync android
```

Then rebuild in Android Studio.

## iOS Note

iOS users should use the web version (Safari → Add to Home Screen) because:
- iOS Wake Lock already works in Safari
- App Store distribution requires $99/year Apple Developer account
- The web PWA works great on iOS

## Project Structure

```
listener-app/
├── capacitor.config.json    # Capacitor configuration
├── package.json             # Node.js dependencies
├── www/                     # Web app files
│   ├── index.html           # Main app
│   └── js/
│       └── capacitor-plugins.js
└── android/                 # Android native project
    └── app/
        └── src/main/
            └── AndroidManifest.xml
```

## Troubleshooting

### App won't connect to server
- Make sure the phone and translator computer are on the same WiFi network
- Check firewall settings on the translator computer
- Try the full URL: `http://192.168.1.50:7860`

### Screen still turns off
- This should NOT happen with the native app
- If it does, check that the app has foreground permissions

### Audio not playing
- Tap the play button in the footer
- Check phone volume
- Some phones need "Allow background audio" permission
