import translator_core as core
try:
    print(f"Google Voices found: {len(core.GOOGLE_VOICES)}")
    print(f"Sample: {core.GOOGLE_VOICES[0]}")
except AttributeError:
    print("Error: GOOGLE_VOICES not found in translator_core")
except Exception as e:
    print(f"Error: {e}")
