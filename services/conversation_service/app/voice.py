"""
Voice Module - Text-to-Speech utilities.
Uses gTTS (Google Text-to-Speech) for reliable TTS in containers.
"""
import re
from io import BytesIO

from gtts import gTTS


# Available languages
SUPPORTED_LANGS = ["en", "es", "fr", "de", "it", "pt", "hi", "ar", "zh-CN", "ja", "ko"]


def strip_markdown(text: str) -> str:
    """
    Remove markdown formatting from text for clean TTS output.
    """
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Remove headers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove bullet points and list markers
    text = re.sub(r'^[\-\*•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    
    # Remove checkboxes
    text = re.sub(r'\[[ x✓✔]\]\s*', '', text)
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove inline code markers
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove emojis (common ones used in our responses)
    emoji_pattern = re.compile("["
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


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
    # Strip markdown for clean TTS
    clean_text = strip_markdown(text)
    
    # Create TTS object
    tts = gTTS(text=clean_text, lang=lang, slow=False)
    
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
