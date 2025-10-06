"""
Language Detection Module

This module provides language detection functionality for audio transcription,
including text-based keyword detection and probe-based detection using ffmpeg.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Any

from txt_audio_to_db.config.transcribe_audio_config import TranscriptionConfig
from ..transcribe_audio_logging import get_logger

# Initialize logger for this module
logger = get_logger('language_detection')


def detect_language_from_text(text: str) -> Optional[str]:
    """
    Simple language detection based on common words and patterns.
    Uses keyword lists from TranscriptionConfig.LANGUAGE_KEYWORDS.
    
    Args:
        text: Text to analyze for language detection
        
    Returns:
        ISO-639-1 code like 'en', 'pt', 'es', etc., or None if uncertain.
    """
    logger.debug(f"Analyzing text for language detection (length: {len(text)} chars)")
    logger.debug(f"Text sample: {text[:100]}...")
    
    text_lower = text.lower()
    
    # Score each language based on keyword matches
    scores = {}
    for lang_code in TranscriptionConfig.get_supported_languages():
        keywords = TranscriptionConfig.get_language_keywords(lang_code)
        score = sum(1 for word in keywords if word in text_lower)
        scores[lang_code] = score
        if score > 0:
            logger.debug(f"Language '{lang_code}' scored {score} keyword matches")
    
    # Find the language with highest score
    max_score = max(scores.values()) if scores else 0
    logger.debug(f"Maximum score: {max_score}")
    
    if max_score > 0:
        # Return the language with the highest score
        for lang, score in scores.items():
            if score == max_score:
                logger.info(f"Detected language from text: {lang} (score: {score})")
                return lang
    
    logger.debug("No language detected from text (no keyword matches)")
    return None


def have_ffmpeg() -> bool:
    """Check if ffmpeg is available in the system PATH."""
    has_ffmpeg = shutil.which("ffmpeg") is not None
    logger.debug(f"FFmpeg availability check: {has_ffmpeg}")
    return has_ffmpeg


def slice_with_ffmpeg(src: Path, seconds: int) -> Path:
    """
    Create a temporary WAV slice from the start of an audio file using ffmpeg.
    
    Args:
        src: Source audio file path
        seconds: Duration of the slice in seconds
        
    Returns:
        Path to the temporary WAV slice file
    """
    logger.debug(f"Creating ffmpeg probe slice: source={src.name}, duration={seconds}s")
    
    # Get FFmpeg settings from config
    ffmpeg_cfg = TranscriptionConfig.FFMPEG_SETTINGS
    temp_cfg = TranscriptionConfig.TEMP_SETTINGS
    
    td = tempfile.mkdtemp(prefix=temp_cfg['probe_prefix'])
    out = Path(td) / "probe.wav"
    logger.debug(f"Temporary probe file: {out}")
    
    # Build ffmpeg command with config settings
    cmd = ["ffmpeg"]
    if ffmpeg_cfg['hide_banner']:
        cmd.append("-hide_banner")
    cmd.extend(["-loglevel", ffmpeg_cfg['loglevel']])
    cmd.extend(["-i", str(src), "-t", str(seconds)])
    cmd.extend(["-ac", str(ffmpeg_cfg['audio_channels'])])
    cmd.extend(["-ar", str(ffmpeg_cfg['sample_rate'])])
    cmd.extend(["-vn", str(out)])
    
    logger.debug(f"Executing ffmpeg command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"FFmpeg probe slice created successfully: {out}")
    except subprocess.CalledProcessError as e:
        # We won't die here; caller can fallback. Return a path that doesn't exist.
        logger.warning(f"FFmpeg failed to create probe slice: {e}")
        print(f"WARNING: ffmpeg failed to create probe slice ({e}). Falling back.", file=sys.stderr)
        return Path("/__ffmpeg_failed__.wav")
    return out


def detect_language_with_probe(client: Any, audio_path: Path, detect_model: str, 
                             probe_seconds: int, use_probe: bool) -> tuple[Optional[str], bool]:
    """
    Try to detect language quickly. Prefer ffmpeg short slice; if unavailable/fails,
    fallback to using the full file with the detect_model.
    
    Args:
        client: OpenAI client instance (required, cannot be None)
        audio_path: Path to the audio file
        detect_model: Model to use for language detection
        probe_seconds: Duration to sample for detection
        use_probe: Whether to use ffmpeg probe (if available)
        
    Returns:
        Tuple of (language_code, ffmpeg_used) where:
        - language_code: ISO-639-1 code like 'en' or 'pt', or None if detection fails
        - ffmpeg_used: Boolean indicating if FFmpeg probe slice was successfully used
    """
    logger.info(f"Starting language detection with probe: file={audio_path.name}, model={detect_model}, "
               f"probe_seconds={probe_seconds}, use_probe={use_probe}")
    
    file_for_probe: Path = audio_path
    cleanup_path: Optional[Path] = None
    ffmpeg_used: bool = False

    if use_probe and have_ffmpeg():
        logger.debug("Attempting to create ffmpeg probe slice...")
        probe = slice_with_ffmpeg(audio_path, probe_seconds)
        if probe.exists():
            file_for_probe = probe
            cleanup_path = probe
            ffmpeg_used = True
            logger.info(f"Using probe slice for detection: {probe}")
        else:
            # ffmpeg failed; we'll fallback to full file
            logger.warning("FFmpeg probe creation failed, using full audio file for detection")
    else:
        if not use_probe:
            logger.debug("Probe disabled, using full audio file for detection")
        else:
            logger.debug("FFmpeg not available, using full audio file for detection")

    # Client must be provided - no fallback creation
    if client is None:
        raise ValueError("Client parameter is required and cannot be None")
    try:
        # Get API settings from config
        response_format = TranscriptionConfig.API_SETTINGS['response_format_probe']
        logger.debug(f"Calling OpenAI API for language detection (format: {response_format})...")
        
        with open(file_for_probe, "rb") as f:
            # Small/fast model for detection - use text format since json doesn't include language
            resp = client.audio.transcriptions.create(
                model=detect_model,
                file=f,
                response_format=response_format,
                temperature=0.0,
            )
        
        logger.debug("API call completed, processing response...")
        
        # Since we can't get language from API response, we'll do simple text-based detection
        text = resp.strip() if isinstance(resp, str) else str(resp).strip()
        logger.debug(f"Transcription response (for detection): {text[:200]}...")
        
        # Simple language detection based on common words/patterns
        logger.debug("Analyzing transcription text for language keywords...")
        lang = detect_language_from_text(text)
        
        if lang:
            logger.info(f"Language detection successful: {lang}")
        else:
            logger.info("Language detection returned None (no strong match)")
        
        return lang, ffmpeg_used
    except Exception as e:
        logger.error(f"Language detection encountered an error: {e}", exc_info=True)
        print(f"WARNING: language detection fallback encountered an error: {e}", file=sys.stderr)
        return None, ffmpeg_used
    finally:
        if cleanup_path and cleanup_path.exists():
            logger.debug(f"Cleaning up temporary probe file: {cleanup_path}")
            try:
                cleanup_path.unlink()
                cleanup_path.parent.rmdir()
                logger.debug("Cleanup completed")
            except Exception as e:
                logger.warning(f"Failed to cleanup probe file: {e}")
