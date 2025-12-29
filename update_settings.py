import json
import os

settings_file = 'settings.json'

try:
    with open(settings_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    current_prompt = data.get('system_prompt_template', '')
    
    # Define the old and new phrases
    old_phrase = "Do not include metadata, timestamps, or system notes in the output — only the clean translated speech."
    new_phrase = "Do not include metadata, timestamps, verse citations, Bible version tags, or system notes in the output — only the clean translated speech."
    
    # Check if we need to update
    if old_phrase in current_prompt:
        data['system_prompt_template'] = current_prompt.replace(old_phrase, new_phrase)
        print("Updating prompt...")
    elif new_phrase in current_prompt:
        print("Prompt already updated.")
    else:
        # If precise match fails, we might just append the restriction
        print("Phrase not found exactly, ensuring restriction is present...")
        # (Optional: force a replace if it's close, but let's stick to safe replace first)
        
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print("Settings saved.")
    print("New Prompt Snippet:", data['system_prompt_template'][-200:])

except Exception as e:
    print(f"Error: {e}")
