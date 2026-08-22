from dotenv import load_dotenv
import os
from pathlib import Path
from openai import AzureOpenAI
from playsound3 import playsound

# -------------------------------------------------------
# Demo 1: Generate Speech with a Serious Tone
#
# Uses gpt-4o-mini-tts via Azure OpenAI.
# Unlike the Speech SDK (which just reads text aloud),
# this model understands *instructions* — you can tell it
# HOW to speak: tone, pace, emotion, accent, etc.
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_SPEECH_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_SPEECH_KEY"),
    api_version="2025-03-01-preview"
)

MODEL = "gpt-4o-mini-tts"
OUTPUT_FILE = Path(__file__).parent / "speech.mp3"

# The text to speak
TEXT = "I enjoy watching movies and TV shows in German."

# The instruction that controls HOW it speaks — this is what makes it different from standard TTS
INSTRUCTIONS = "Translate this into german and read it like a movie trailer. Use a deep, dramatic voice with a slow pace and serious tone."


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 50)
    print("   Demo 1: Generate Speech with Serious Tone")
    print("   Model: gpt-4o-mini-tts")
    print("=" * 50)

    print(f"\nText     : {TEXT}")
    print(f"Tone     : {INSTRUCTIONS}")
    print("\nGenerating speech...\n")

    with client.audio.speech.with_streaming_response.create(
        model=MODEL,
        voice="sage",
        input=TEXT,
        instructions=INSTRUCTIONS,
    ) as response:
        response.stream_to_file(OUTPUT_FILE)

    print(f"Saved to : {OUTPUT_FILE.name}")
    print("Playing audio...\n")
    playsound(str(OUTPUT_FILE))


if __name__ == "__main__":
    main()
