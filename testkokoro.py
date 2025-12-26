# OpenAI-compatible streaming
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8880/v1", api_key="not-needed")

# Stream to file
with client.audio.speech.with_streaming_response.create(
    model="kokoro",
    voice="af_bella",
    input="Hello world!"
) as response:
    response.stream_to_file("output.mp3")

# Stream to speakers (requires PyAudio)
import pyaudio
player = pyaudio.PyAudio().open(
    format=pyaudio.paInt16, 
    channels=1, 
    rate=24000, 
    output=True
)

with client.audio.speech.with_streaming_response.create(
    model="kokoro",
    voice="af_bella",
    response_format="pcm",
    input="Hello world!"
) as response:
    for chunk in response.iter_bytes(chunk_size=1024):
        player.write(chunk)