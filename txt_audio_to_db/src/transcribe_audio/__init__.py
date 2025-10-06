"""
Audio Transcription Package Entry Point

This package provides audio transcription functionality with language detection.
"""

from .core import transcribe_audio, validate_audio_file, detect_language_from_text, detect_language_with_probe
from txt_audio_to_db.config.transcribe_audio_config import TranscriptionConfig

__version__ = "1.0.0"
__all__ = [
    'transcribe_audio',
    'validate_audio_file',
    'detect_language_from_text', 
    'detect_language_with_probe',
    'TranscriptionConfig'
]

