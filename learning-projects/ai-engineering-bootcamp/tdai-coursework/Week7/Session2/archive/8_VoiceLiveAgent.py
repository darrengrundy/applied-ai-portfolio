from dotenv import load_dotenv
import os
import asyncio
import base64
from pathlib import Path
import pyaudio
from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    RequestSession,
    Modality,
    InputAudioFormat,
    OutputAudioFormat,
    ServerVad,
    ServerEventType,
    AzureStandardVoice,
)

# -------------------------------------------------------
# Demo 2: Standalone Real-Time Voice Agent
#
# This is the code equivalent of the Foundry Portal voice
# session from Demo 1 — the same cloud infrastructure,
# now in a standalone Python application.
#
# Flow (matches the slides):
#   Step 1 – Connect      : open WebSocket to Azure Voice Live
#   Step 2 – Init Audio   : set up PyAudio mic + speaker streams
#   Step 3 – Setup Session: configure voice, language model, VAD
#   Step 4 – Process Events: stream mic → AI → speaker in real time
#
# Install:
#   pip install "azure-ai-voicelive[aiohttp]" pyaudio python-dotenv
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
ENDPOINT  = os.getenv("VOICELIVE_ENDPOINT")
KEY       = os.getenv("VOICELIVE_KEY")
MODEL     = os.getenv("VOICELIVE_MODEL", "gpt-5.3-chat")

# PyAudio settings — must match the model's expected format
RATE      = 24000
CHANNELS  = 1
CHUNK     = 4096
FORMAT    = pyaudio.paInt16

SYSTEM_PROMPT = (
    "You are a helpful TDAI Bank voice assistant. "
    "Answer questions about accounts, balances, and banking services. "
    "Keep responses short and clear — this is a real-time voice interface."
)


# -------------------------------------------------------
# Step 4a — continuously send mic audio to the connection
# -------------------------------------------------------
async def stream_microphone(conn, mic_stream):
    """Read chunks from the microphone and send base64-encoded PCM to the model."""
    while True:
        raw_audio = mic_stream.read(CHUNK, exception_on_overflow=False)
        encoded   = base64.b64encode(raw_audio).decode("utf-8")
        await conn.input_audio_buffer.append(audio=encoded)
        await asyncio.sleep(0)  # yield to let the event loop breathe


# -------------------------------------------------------
# Step 4b — receive events and play back AI audio
# -------------------------------------------------------
async def process_events(conn, speaker_stream):
    """Handle server events: print transcripts, play audio deltas."""
    async for evt in conn:

        if evt.type == ServerEventType.SESSION_UPDATED:
            print("Session ready — speak into your microphone.\n")

        elif evt.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            print("(you are speaking...)")

        elif evt.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            # Stream the AI's text response to console as it arrives
            print(evt.delta, end="", flush=True)

        elif evt.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            # Decode and play each audio chunk in real time
            # Azure Neural Voice may return bytes directly or base64 without padding
            if isinstance(evt.delta, (bytes, bytearray)):
                audio_bytes = evt.delta
            else:
                audio_bytes = base64.b64decode(evt.delta + "==")
            speaker_stream.write(audio_bytes)

        elif evt.type == ServerEventType.RESPONSE_DONE:
            print("\n")  # new line after response

        elif evt.type == ServerEventType.ERROR:
            print(f"\nError: {evt.error.message}")
            break


# -------------------------------------------------------
# Main
# -------------------------------------------------------
async def main():
    print("=" * 50)
    print("   TDAI Bank — Real-Time Voice Agent")
    print("   Powered by Azure Voice Live SDK")
    print("=" * 50)
    print("\nConnecting to Azure Voice Live...\n")

    # Step 2 — Initialise Audio (PyAudio mic + speaker)
    pa = pyaudio.PyAudio()
    mic_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=RATE,
        input=True, frames_per_buffer=CHUNK
    )
    speaker_stream = pa.open(
        format=FORMAT, channels=CHANNELS, rate=RATE,
        output=True
    )

    try:
        # Step 1 — Connect (opens WebSocket to Azure Voice Live)
        async with connect(
            endpoint=ENDPOINT,
            credential=AzureKeyCredential(KEY),
            model=MODEL,
        ) as conn:

            # Step 3 — Setup Session
            await conn.session.update(session=RequestSession(
                modalities=[Modality.TEXT, Modality.AUDIO],
                instructions=SYSTEM_PROMPT,
                input_audio_format=InputAudioFormat.PCM16,
                output_audio_format=OutputAudioFormat.PCM16,
                input_audio_sampling_rate=RATE,
                voice=AzureStandardVoice(name="en-US-AvaNeural"),
                turn_detection=ServerVad(
                    threshold=0.5,
                    prefix_padding_ms=300,
                    silence_duration_ms=600,
                ),
            ))

            print("Connected. Say something — press Ctrl+C to exit.\n")
            print("-" * 50)

            # Step 4 — Process Events (mic → AI → speaker, runs concurrently)
            await asyncio.gather(
                stream_microphone(conn, mic_stream),
                process_events(conn, speaker_stream),
            )

    except KeyboardInterrupt:
        print("\n\nSession ended.")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        pa.terminate()


if __name__ == "__main__":
    asyncio.run(main())
