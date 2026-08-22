from dotenv import load_dotenv
import os
import threading
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# -------------------------------------------------------
# Demo: Doctor-Patient Consultation Notes Generator
#
# Step 1 – Feed a .wav audio file into the SpeechRecognizer (ASR).
#           Uses continuous recognition to capture the full conversation.
# Step 2 – Pass the transcript to an LLM via Azure AI Foundry to
#           generate structured consultation notes (SOAP format).
#
# Usage:
#   python 4_DoctorConsultationNotes.py
#   Place your consultation audio file at: audio/consultation.wav
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
FOUNDRY_KEY = os.getenv("FOUNDRY_KEY")
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
SPEECH_REGION = os.getenv("SPEECH_REGION", "australiaeast")
MODEL_NAME = os.getenv("FOUNDRY_MODEL", "gpt-4o-mini")

AUDIO_FILE = os.path.join(os.path.dirname(__file__), "audio", "consultation.wav")


# -------------------------------------------------------
# Step 1: Transcribe the audio file using continuous ASR
# -------------------------------------------------------
def transcribe_audio(audio_path):
    print(f"\n[1/2] Transcribing: {os.path.basename(audio_path)}")
    print("-" * 50)

    speech_config = speechsdk.SpeechConfig(subscription=FOUNDRY_KEY, region=SPEECH_REGION)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    transcript_parts = []
    done = threading.Event()

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"  {evt.result.text}")
            transcript_parts.append(evt.result.text)

    def on_stop(evt):
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.session_stopped.connect(on_stop)
    recognizer.canceled.connect(on_stop)

    recognizer.start_continuous_recognition_async()
    done.wait()
    recognizer.stop_continuous_recognition_async()

    full_transcript = " ".join(transcript_parts)
    print(f"\n  Transcription complete. ({len(transcript_parts)} segments)")
    return full_transcript


# -------------------------------------------------------
# Step 2: Generate consultation notes from the transcript
# -------------------------------------------------------
def generate_notes(transcript):
    print("\n[2/2] Generating consultation notes...")
    print("-" * 50)

    client = ChatCompletionsClient(
        endpoint=FOUNDRY_ENDPOINT,
        credential=AzureKeyCredential(FOUNDRY_KEY)
    )

    prompt = f"""You are a medical scribe. Based on the following doctor-patient conversation transcript,
generate structured consultation notes in SOAP format.

Transcript:
{transcript}

Generate the notes with these clearly labelled sections:
- SUBJECTIVE: What the patient reports (symptoms, history, concerns)
- OBJECTIVE: Any observable findings mentioned
- ASSESSMENT: The doctor's assessment or likely diagnosis
- PLAN: Recommended treatments, tests, follow-ups, or referrals

Be concise and use clinical language."""

    response = client.complete(
        model=MODEL_NAME,
        messages=[
            SystemMessage("You are an expert medical scribe that produces clear, accurate consultation notes."),
            UserMessage(prompt)
        ]
    )

    return response.choices[0].message.content


# -------------------------------------------------------
# Main
# -------------------------------------------------------
def main():
    print("=" * 50)
    print("  Doctor-Patient Consultation Notes Generator")
    print("=" * 50)

    if not os.path.exists(AUDIO_FILE):
        print(f"\nAudio file not found: {AUDIO_FILE}")
        print("Please place a .wav consultation recording at:")
        print(f"  {AUDIO_FILE}")
        return

    # Step 1: Transcribe
    transcript = transcribe_audio(AUDIO_FILE)

    if not transcript.strip():
        print("\nNo speech detected in the audio file.")
        return

    # Step 2: Generate notes
    notes = generate_notes(transcript)

    # Display
    print("\n" + "=" * 50)
    print("  CONSULTATION NOTES")
    print("=" * 50)
    print(notes)

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), "consultation_notes.txt")
    with open(output_path, "w") as f:
        f.write("TRANSCRIPT\n" + "=" * 50 + "\n")
        f.write(transcript + "\n\n")
        f.write("CONSULTATION NOTES\n" + "=" * 50 + "\n")
        f.write(notes + "\n")

    print(f"\nNotes saved to: {output_path}")


if __name__ == "__main__":
    main()
