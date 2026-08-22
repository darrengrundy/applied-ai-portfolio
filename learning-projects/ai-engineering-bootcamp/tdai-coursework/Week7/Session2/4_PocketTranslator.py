from dotenv import load_dotenv
import os
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk

# -------------------------------------------------------
# Demo: Personal Pocket Translator
#
# Scenario: Tourist in a pharmacy in Tokyo needs to
# explain an allergy to a pharmacist.
#
# Flow:
#   1. Listen to the user speak in English (microphone)
#   2. Translate the speech using TranslationRecognizer
#   3. Synthesize the translated text in the target language
#      and play it through the speakers
#
# The TranslationRecognizer does steps 1 + 2 in a single call —
# it recognises and translates simultaneously. A separate
# SpeechSynthesizer is then used for step 3.
# -------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")
FOUNDRY_KEY = os.getenv("FOUNDRY_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION", "australiaeast")

# Supported target languages and their neural voices
LANGUAGES = {
    "ja": ("Japanese",    "ja-JP-NanamiNeural"),
    "fr": ("French",      "fr-FR-DeniseNeural"),
    "es": ("Spanish",     "es-ES-ElviraNeural"),
    "hi": ("Hindi",       "hi-IN-SwaraNeural"),
    "zh": ("Chinese",     "zh-CN-XiaoxiaoNeural"),
}


def build_translation_config():
    """
    SpeechTranslationConfig handles both recognition (STT) and translation.
    A separate SpeechConfig is needed for synthesis (TTS) — they cannot share
    the same config object.
    """
    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=FOUNDRY_KEY, region=SPEECH_REGION
    )
    translation_config.speech_recognition_language = "en-US"
    for lang_code in LANGUAGES:
        translation_config.add_target_language(lang_code)
    return translation_config


def translate_and_speak(target_lang, translation_config):
    """
    Listen via microphone → translate → speak in target language.
    """
    lang_name, voice_name = LANGUAGES[target_lang]
    print(f"\nSpeak now in English (translating to {lang_name})...")
    print('Try: "I have an allergy. I need some medicine for my allergy."\n')

    # --- Step 1 + 2: Recognise and translate from microphone ---
    # No audio_config = use default microphone
    recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=translation_config
    )

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.TranslatedSpeech:
        english_text = result.text
        translated_text = result.translations[target_lang]

        print(f"  English  : {english_text}")
        print(f"  {lang_name:<9}: {translated_text}")

        # --- Step 3: Synthesize the translation to speakers ---
        speech_config = speechsdk.SpeechConfig(
            subscription=FOUNDRY_KEY, region=SPEECH_REGION
        )
        speech_config.speech_synthesis_voice_name = voice_name

        # Save to file AND play through speakers
        output_file = os.path.join(os.path.dirname(__file__), "translation_output.wav")
        audio_out = speechsdk.audio.AudioOutputConfig(
            filename=output_file, use_default_speaker=True
        )
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_out
        )

        speak_result = synthesizer.speak_text_async(translated_text).get()

        if speak_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"  (audio saved to translation_output.wav)")
        elif speak_result.reason == speechsdk.ResultReason.Canceled:
            details = speak_result.cancellation_details
            print(f"  Synthesis failed: {details.error_details}")

    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("  No speech detected. Please try again.")

    elif result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(f"  Recognition canceled: {details.reason}")
        if details.reason == speechsdk.CancellationReason.Error:
            print(f"  Error: {details.error_details}")


def main():
    try:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 50)
        print("   Personal Pocket Translator")
        print("   Scenario: Tourist in a Tokyo pharmacy")
        print("=" * 50)

        translation_config = build_translation_config()

        target_lang = ""
        while target_lang != "quit":
            print("\nSelect a target language:")
            for code, (name, _) in LANGUAGES.items():
                print(f"  {code} = {name}")
            print("  quit = Exit")

            target_lang = input("\n> ").strip().lower()

            if target_lang in LANGUAGES:
                translate_and_speak(target_lang, translation_config)
            elif target_lang != "quit":
                print("Invalid option — please enter one of the language codes above.")

        print("\nGoodbye!")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()
