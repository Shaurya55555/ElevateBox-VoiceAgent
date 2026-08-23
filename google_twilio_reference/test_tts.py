"""
Sanity check for Google Cloud TTS credentials + Telugu/Hindi voice
availability, independent of the telephony pipeline. Writes a playable
WAV file (converted from the MULAW/8kHz telephony format we actually use
on calls) so you can listen to it directly.

Usage:
    python test_tts.py
"""

import wave

from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

SAMPLES = {
    "hindi": "namaste, main Shaurya ki taraf se baat kar rahi hoon.",
    "telugu": "namaskaram, nenu Shaurya tarafu nunchi matladutunnanu.",
    "english": "Hi, this is Ananya calling on behalf of Shaurya.",
}

VOICE_BY_LANG = {
    "hindi": ("hi-IN", "hi-IN-Wavenet-A"),
    "telugu": ("te-IN", "te-IN-Standard-A"),
    "english": ("en-IN", "en-IN-Wavenet-A"),
}


def synthesize_to_wav(text: str, language_code: str, voice_name: str, out_path: str):
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=16000
    )
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(response.audio_content)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    for lang, text in SAMPLES.items():
        lang_code, voice_name = VOICE_BY_LANG[lang]
        try:
            synthesize_to_wav(text, lang_code, voice_name, f"test_tts_{lang}.wav")
        except Exception as exc:  # noqa: BLE001
            print(f"{lang} FAILED: {exc}")
