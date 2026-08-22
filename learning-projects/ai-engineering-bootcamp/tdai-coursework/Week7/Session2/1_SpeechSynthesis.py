import os
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# -------------------------------------------------------
# Azure Speech Service credentials loaded from .env
# SPEECH_KEY: your Speech resource key (or Foundry multi-service key)
# SPEECH_REGION: e.g. "australiaeast", "eastus"
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION", "australiaeast")


def create_speech_config():
    """Create a SpeechConfig and set a neural voice for synthesis."""
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    # Use a neural voice for natural-sounding speech
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
    return speech_config


def record_greeting(speech_config):
    """
    Synthesize a user-provided greeting message to a WAV file (greeting.wav).
    Demonstrates: Text-to-Speech (TTS) with file output.
    """
    print("\n--- Record a Greeting (Text to Speech) ---")
    greeting_message = input("Enter your greeting message: ")

    output_file = "greeting.wav"

    # Route audio output to a file instead of the speaker
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    print(f"Synthesizing speech and saving to '{output_file}'...")
    result = synthesizer.speak_text_async(greeting_message).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Done. Greeting saved to '{output_file}'")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"Synthesis canceled: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation.error_details}")


def transcribe_messages(speech_config):
    """
    Transcribe all .wav files found in the 'messages/' folder.
    Demonstrates: Speech-to-Text (STT) from an audio file.
    """
    print("\n--- Transcribe Messages (Speech to Text) ---")
    messages_folder = os.path.join(os.path.dirname(__file__), "messages")

    if not os.path.exists(messages_folder):
        os.makedirs(messages_folder)

    wav_files = [f for f in os.listdir(messages_folder) if f.endswith(".wav")]

    if not wav_files:
        print(f"No .wav files found in '{messages_folder}'.")
        print("Tip: Copy .wav audio files into that folder and run option 2 again.")
        return

    for file_name in wav_files:
        file_path = os.path.join(messages_folder, file_name)
        print(f"\nTranscribing: {file_name}")

        # Route audio input from a file
        audio_config = speechsdk.audio.AudioConfig(filename=file_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"  Transcription: {result.text}")
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print(f"  No speech recognized: {result.no_match_details}")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f"  Recognition canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                print(f"  Error details: {cancellation.error_details}")


def main():
    os.system("cls" if os.name == "nt" else "clear")

    speech_config = create_speech_config()

    choice = ""
    while choice != "3":
        choice = input(
            "\nChoose an option:\n"
            "  1: Record a greeting  (Text -> Speech saved to greeting.wav)\n"
            "  2: Transcribe messages (Speech files -> Text)\n"
            "  3: Exit\n"
            "> "
        )

        if choice == "1":
            record_greeting(speech_config)
        elif choice == "2":
            transcribe_messages(speech_config)
        elif choice == "3":
            print("Exiting.")
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    main()
