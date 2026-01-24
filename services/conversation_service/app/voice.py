"""
Voice Module - Text-to-Speech utilities.
Uses gTTS (Google Text-to-Speech) for reliable TTS in containers.
"""
import tempfile
import os
from io import BytesIO

from gtts import gTTS


# Available languages
SUPPORTED_LANGS = ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh-CN", "ja", "ko"]


def text_to_speech_sync(text: str, lang: str = "en") -> bytes:
    """
    Convert text to speech audio bytes (MP3 format).
    Synchronous version for simplicity.
    
    Args:
        text: The text to convert to speech.
        lang: Language code (default: en).
    
    Returns:
        Audio data as MP3 bytes.
    """
    # Create TTS object
    tts = gTTS(text=text, lang=lang, slow=False)
    
    # Write to BytesIO buffer
    audio_buffer = BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    
    return audio_buffer.read()


async def text_to_speech(text: str, lang: str = "en") -> bytes:
    """
    Async wrapper for text_to_speech.
    gTTS is synchronous, so we just call the sync version.
    
    Args:
        text: The text to convert to speech.
        lang: Language code (default: en).
    
    Returns:
        Audio data as MP3 bytes.
    """
    return text_to_speech_sync(text, lang)


def get_available_voices() -> list[dict]:
    """
    Get list of available TTS languages/voices.
    
    Returns:
        List of voice metadata dictionaries.
    """
    return [
        {"id": lang, "name": f"Google TTS ({lang})", "locale": lang}
        for lang in SUPPORTED_LANGS
    ]
