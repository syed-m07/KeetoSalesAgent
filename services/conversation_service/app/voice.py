"""
Voice Module - Text-to-Speech utilities.
Uses Edge TTS (Microsoft Neural TTS) for natural-sounding voices.
Falls back to gTTS if Edge TTS fails.
"""
import re

from io import BytesIO
from typing import Optional

import edge_tts
from gtts import gTTS


# Default voice for "Ravi" - Indian English Male (natural neural voice)
DEFAULT_VOICE = "en-IN-PrabhatNeural"

# Available Edge TTS voices (popular selections)
EDGE_VOICES = {
    "ravi": "en-IN-PrabhatNeural",      # Indian English Male (default)
    "priya": "en-IN-NeerjaNeural",      # Indian English Female
    "guy": "en-US-GuyNeural",           # US English Male
    "aria": "en-US-AriaNeural",         # US English Female
    "ryan": "en-GB-RyanNeural",         # British English Male
    "sonia": "en-GB-SoniaNeural",       # British English Female
}

# Legacy language support (for backward compatibility)
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


async def text_to_speech_edge(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    Convert text to speech using Edge TTS (Microsoft Neural voices).
    
    Args:
        text: The text to convert to speech.
        voice: Edge TTS voice name (default: en-IN-PrabhatNeural).
    
    Returns:
        Audio data as MP3 bytes.
    """
    clean_text = strip_markdown(text)
    
    if not clean_text:
        return b""
    
    # Create Edge TTS communicate object
    communicate = edge_tts.Communicate(clean_text, voice)
    
    # Collect audio chunks
    audio_buffer = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    
    audio_buffer.seek(0)
    return audio_buffer.read()


def text_to_speech_gtts(text: str, lang: str = "en") -> bytes:
    """
    Fallback: Convert text to speech using gTTS (Google TTS).
    
    Args:
        text: The text to convert to speech.
        lang: Language code (default: en).
    
    Returns:
        Audio data as MP3 bytes.
    """
    clean_text = strip_markdown(text)
    
    if not clean_text:
        return b""
    
    tts = gTTS(text=clean_text, lang=lang, slow=False)
    audio_buffer = BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    return audio_buffer.read()


def text_to_speech_sync(text: str, lang: str = "en", voice: Optional[str] = None) -> bytes:
    """
    Synchronous wrapper for TTS. Uses Edge TTS via CLI subprocess for stability, falls back to gTTS.
    
    Args:
        text: The text to convert to speech.
        lang: Language code (for gTTS fallback).
        voice: Edge TTS voice name (optional, uses Ravi's voice by default).
    
    Returns:
        Audio data as MP3 bytes.
    """
    # Use Edge TTS with default Ravi voice
    selected_voice = voice or EDGE_VOICES.get("ravi", DEFAULT_VOICE)
    clean_text = strip_markdown(text)
    
    try:
        # Use subprocess to call edge-tts CLI directly
        # This avoids asyncio loop nesting issues in sync contexts
        import subprocess
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_path = temp_audio.name
            
        # Run edge-tts CLI command
        # edge-tts --text "Hello" --write-media /tmp/output.mp3 --voice en-IN-PrabhatNeural
        subprocess.run(
            ["edge-tts", "--text", clean_text, "--write-media", temp_path, "--voice", selected_voice],
            check=True,
            capture_output=True
        )
        
        # Read the generated file
        with open(temp_path, "rb") as f:
            audio_data = f.read()
            
        # Cleanup
        os.unlink(temp_path)
        
        if audio_data:
            return audio_data
            
    except Exception as e:
        print(f"⚠️ Edge TTS CLI failed: {e}, falling back to gTTS")
    
    # Fallback to gTTS
    return text_to_speech_gtts(text, lang)


async def text_to_speech(text: str, lang: str = "en", voice: Optional[str] = None) -> bytes:
    """
    Async TTS. Uses Edge TTS library directly.
    """
    selected_voice = voice or EDGE_VOICES.get("ravi", DEFAULT_VOICE)
    
    try:
        audio = await text_to_speech_edge(text, selected_voice)
        if audio:
            return audio
    except Exception as e:
        print(f"⚠️ Edge TTS failed: {e}, falling back to gTTS")
    
    # Fallback to gTTS (sync)
    return text_to_speech_gtts(text, lang)


def get_available_voices() -> list[dict]:
    """
    Get list of available TTS voices.
    
    Returns:
        List of voice metadata dictionaries.
    """
    voices = [
        {"id": key, "name": value, "locale": value.split("-")[0] + "-" + value.split("-")[1], "quality": "neural"}
        for key, value in EDGE_VOICES.items()
    ]
    # Add legacy gTTS voices
    voices.extend([
        {"id": lang, "name": f"Google TTS ({lang})", "locale": lang, "quality": "standard"}
        for lang in SUPPORTED_LANGS
    ])
    return voices
