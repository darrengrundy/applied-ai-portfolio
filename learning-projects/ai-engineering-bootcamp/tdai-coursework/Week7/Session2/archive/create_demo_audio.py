from dotenv import load_dotenv
import os
import wave
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk

# -------------------------------------------------------
# Generates a demo doctor-patient consultation WAV file
# using two different neural voices, then stitches the
# lines together into a single audio/consultation.wav
#
# Doctor voice : en-AU-WilliamNeural  (Australian male)
# Patient voice: en-AU-NatashaNeural  (Australian female)
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
FOUNDRY_KEY = os.getenv("FOUNDRY_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION", "australiaeast")

SCRIPT = [
    ("doctor",  "Good morning. How are you feeling today?"),
    ("patient", "Not great, doctor. I've had a really bad headache for the past three days, and I've been feeling quite tired."),
    ("doctor",  "I'm sorry to hear that. Can you describe the headache — is it on one side or both sides?"),
    ("patient", "It's mostly on the right side, and it gets worse when I'm in bright light."),
    ("doctor",  "Have you had any nausea or vomiting with it?"),
    ("patient", "Yes, a bit of nausea, but no vomiting."),
    ("doctor",  "Any fever or neck stiffness?"),
    ("patient", "No fever that I know of, but my neck does feel a little stiff."),
    ("doctor",  "Have you taken anything for the pain?"),
    ("patient", "Just some paracetamol, but it doesn't seem to be helping much."),
    ("doctor",  "Based on what you're describing, this sounds like it could be a migraine. "
                "I'd like to run a few blood tests to rule out anything else. "
                "I'll prescribe a stronger pain relief and something to help with the nausea. "
                "Please rest in a quiet, dark room as much as possible. "
                "If the headache worsens or you develop a high fever, come back immediately."),
    ("patient", "Thank you, doctor. Should I avoid anything?"),
    ("doctor",  "Yes — avoid bright screens and loud noises, stay hydrated, and get plenty of rest. "
                "Come back in a week if you're not feeling better."),
    ("patient", "Thank you very much."),
    ("doctor",  "Take care. See you soon."),
]

VOICES = {
    "doctor":  "en-AU-WilliamNeural",
    "patient": "en-AU-NatashaNeural",
}


def synthesize_line(speech_config, text, voice, output_path):
    """Synthesize one line of dialogue to a WAV file."""
    speech_config.speech_synthesis_voice_name = voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(text).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(f"Synthesis failed for: {text[:40]}... — {result.cancellation_details.error_details}")


def concatenate_wavs(input_files, output_file):
    """Stitch multiple WAV files into one."""
    params = None
    frames = []

    for path in input_files:
        with wave.open(path, "rb") as wf:
            if params is None:
                params = wf.getparams()
            frames.append(wf.readframes(wf.getnframes()))

    with wave.open(output_file, "wb") as wf:
        wf.setparams(params)
        for f in frames:
            wf.writeframes(f)


def main():
    speech_config = speechsdk.SpeechConfig(subscription=FOUNDRY_KEY, region=SPEECH_REGION)

    audio_dir = os.path.join(os.path.dirname(__file__), "audio")
    os.makedirs(audio_dir, exist_ok=True)

    temp_files = []

    print("Synthesizing consultation lines...")
    for i, (speaker, text) in enumerate(SCRIPT):
        temp_path = os.path.join(audio_dir, f"_line_{i:02d}.wav")
        print(f"  [{speaker:7s}] {text[:60]}{'...' if len(text) > 60 else ''}")
        synthesize_line(speech_config, text, VOICES[speaker], temp_path)
        temp_files.append(temp_path)

    output_path = os.path.join(audio_dir, "consultation.wav")
    print(f"\nStitching {len(temp_files)} lines into consultation.wav...")
    concatenate_wavs(temp_files, output_path)

    # Clean up temp files
    for f in temp_files:
        os.remove(f)

    print(f"Done. Saved to: {output_path}")
    print("\nNow run: python 4_DoctorConsultationNotes.py")


if __name__ == "__main__":
    main()
