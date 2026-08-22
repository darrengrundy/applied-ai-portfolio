from dotenv import load_dotenv
import os
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk
from playsound3 import playsound

# -------------------------------------------------------
# This example uses your Azure AI Foundry multi-service resource.
# The Foundry key works directly with the Speech SDK — you just
# supply the region instead of the full endpoint URL.
#
# Create a .env file in this folder with:
#   FOUNDRY_KEY=your-foundry-key
#   SPEECH_REGION=australiaeast
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
foundry_key = os.getenv("FOUNDRY_KEY")
speech_region = os.getenv("SPEECH_REGION", "australiaeast")


def main():
    try:
        os.system("cls" if os.name == "nt" else "clear")

        # Create speech config from Foundry key + region
        speech_config = speechsdk.SpeechConfig(subscription=foundry_key, region=speech_region)
        speech_config.speech_synthesis_voice_name = "en-AU-NatashaNeural"  # Australian English voice

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

    except Exception as ex:
        print(ex)


def record_greeting(speech_config):
    """Text-to-Speech: synthesize a greeting message and save it to greeting.wav"""
    print("\n--- Record a Greeting ---")
    greeting_message = input("Enter your greeting message: ")

    output_file = os.path.join(os.path.dirname(__file__), "greeting.wav")

    # Send synthesized audio to a file
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    print("Synthesizing speech...")
    result = synthesizer.speak_text_async(greeting_message).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Greeting saved to '{output_file}'")
        playsound(output_file)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"Synthesis canceled: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation.error_details}")


def transcribe_messages(speech_config):
    """Speech-to-Text: play and transcribe all .wav files in the messages/ folder"""
    print("\n--- Transcribe Messages ---")
    messages_folder = os.path.join(os.path.dirname(__file__), "messages")

    if not os.path.exists(messages_folder):
        os.makedirs(messages_folder)

    wav_files = [f for f in os.listdir(messages_folder) if f.endswith(".wav")]

    if not wav_files:
        print(f"No .wav files found in '{messages_folder}'.")
        print("Tip: add .wav files to that folder and run option 2 again.")
        return

    for file_name in wav_files:
        file_path = os.path.join(messages_folder, file_name)
        print(f"\nPlaying and transcribing: {file_name}")
        playsound(file_path)

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


if __name__ == "__main__":
    main()
