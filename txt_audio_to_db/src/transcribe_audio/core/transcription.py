"""
Transcription Module

This module provides the main transcription functionality for audio files,
including language detection and full transcription using OpenAI's API.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from txt_audio_to_db.config.transcribe_audio_config import TranscriptionConfig
from ..transcribe_audio_logging import get_logger

# Initialize logger for this module
logger = get_logger('transcription')


def validate_audio_file(audio_path: str) -> Path:
    """
    Validate audio file path and return resolved Path object.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Resolved Path object
        
    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If file type is not supported
    """
    logger.debug(f"Validating audio path: {audio_path}")
    audio_path_obj = Path(audio_path).expanduser().resolve()
    logger.debug(f"Resolved path: {audio_path_obj}")
    
    if not audio_path_obj.exists() or not audio_path_obj.is_file():
        logger.error(f"Audio file not found: {audio_path_obj}")
        raise FileNotFoundError(f"Audio file not found: {audio_path_obj}")
    
    logger.debug(f"File exists, checking extension: {audio_path_obj.suffix}")
    if not TranscriptionConfig.is_extension_allowed(audio_path_obj.suffix):
        allowed = ', '.join(sorted(TranscriptionConfig.ALLOWED_EXTENSIONS))
        logger.error(f"Unsupported file type: {audio_path_obj.suffix}")
        raise ValueError(f"Unsupported file type '{audio_path_obj.suffix}'. Use: {allowed}")
    
    logger.info(f"Audio file validated: {audio_path_obj.name} ({audio_path_obj.suffix})")
    return audio_path_obj


def transcribe_full(client, audio_path: Path, model: str, 
                   language: Optional[str], temperature: float) -> Dict:
    """
    Perform full transcription of an audio file using OpenAI's API.
    
    Args:
        client: OpenAI client instance
        audio_path: Path to the audio file
        model: Model to use for transcription
        language: ISO-639-1 language code (optional)
        temperature: Decoding temperature
        
    Returns:
        Dictionary containing transcription results and metadata
    """
    logger.debug(f"Starting full transcription: file={audio_path.name}, model={model}, language={language}, temp={temperature}")
    
    # Get API settings from config
    response_format = TranscriptionConfig.API_SETTINGS['response_format_main']
    logger.debug(f"Using response format: {response_format}")
    
    logger.debug(f"Opening audio file: {audio_path}")
    with open(audio_path, "rb") as f:
        logger.debug(f"Calling OpenAI API for transcription...")
        resp = client.audio.transcriptions.create(
            model=model,
            file=f,
            response_format=response_format,
            temperature=temperature,
            **({"language": language} if language else {})
        )
    
    logger.debug("API call completed, normalizing response to dict")
    
    # Normalize to dict
    try:
        result = resp.model_dump()
        logger.debug(f"Response normalized via model_dump()")
        return result
    except Exception:
        try:
            result = resp.to_dict()
            logger.debug(f"Response normalized via to_dict()")
            return result
        except Exception:
            result = json.loads(str(resp))
            logger.debug(f"Response normalized via json.loads()")
            return result


def transcribe_audio(audio_path: str, 
                    model: Optional[str] = None,
                    detect_model: Optional[str] = None,
                    language: Optional[str] = None,
                    probe_seconds: int = None,
                    use_probe: bool = True,
                    language_routing: bool = False,
                    temperature: float = None,
                    client=None) -> Dict:
    """
    Main transcription function that handles the complete transcription workflow.
    
    This is the primary entry point for transcription functionality that can be used
    by different interfaces (CLI, web API, etc.).
    
    Args:
        audio_path: Path to the audio file (MP3, M4A, or WAV)
        model: Model to use for main transcription (default from config)
        detect_model: Model to use for language detection (default from config)
        language: ISO-639-1 language code to force (optional)
        probe_seconds: Seconds to sample for language detection (default from config)
        use_probe: Whether to use ffmpeg probe for language detection
        language_routing: Whether to enable keyword-based language routing
        temperature: Decoding temperature (default from config)
        client: OpenAI client instance (optional, will create if not provided)
        
    Returns:
        Dictionary containing transcription results and metadata
        
    Raises:
        ImportError: If OpenAI SDK is not installed
        FileNotFoundError: If audio file doesn't exist
        ValueError: If file type is not supported
    """
    logger.info(f"transcribe_audio called for: {audio_path}")
    logger.debug(f"Parameters: model={model}, detect_model={detect_model}, language={language}, "
                f"probe_seconds={probe_seconds}, use_probe={use_probe}, language_routing={language_routing}, "
                f"temperature={temperature}")
    
    # Get defaults from config
    model = model or TranscriptionConfig.get_main_model()
    detect_model = detect_model or TranscriptionConfig.get_probe_model()
    temperature = temperature if temperature is not None else TranscriptionConfig.get_default('temperature')
    probe_seconds = probe_seconds if probe_seconds is not None else TranscriptionConfig.get_default('probe_seconds')
    language_routing = language_routing if language_routing is not None else TranscriptionConfig.get_default('language_routing')
    
    logger.debug(f"Configuration resolved: model={model}, detect_model={detect_model}, temperature={temperature}, "
                f"probe_seconds={probe_seconds}, language_routing={language_routing}")
    
    # Initialize client if not provided
    if client is None:
        logger.debug("Creating new OpenAI client")
        try:
            client = TranscriptionConfig.get_client()
        except (ImportError, ValueError) as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            raise
    else:
        logger.debug("Using provided OpenAI client")
    
    # Validate audio file
    audio_path_obj = validate_audio_file(audio_path)
    
    # Step 1: Language selection
    selected_lang = language
    logger.debug(f"Language selection phase: forced_language={language}, language_routing={language_routing}")
    
    # Only do language routing if explicitly enabled and no language forced
    ffmpeg_used = False
    if not selected_lang and language_routing:
        logger.info("Language routing enabled, attempting detection...")
        from .language_detection import detect_language_with_probe
        
        detected, ffmpeg_used = detect_language_with_probe(
            client=client,
            audio_path=audio_path_obj,
            detect_model=detect_model,
            probe_seconds=max(5, probe_seconds),
            use_probe=use_probe
        )
        selected_lang = detected
        logger.info(f"Language detection result: {selected_lang or 'None (will use Whisper auto-detect)'}")
        if ffmpeg_used:
            logger.info("FFmpeg probe slice used for fast language detection")
        else:
            logger.info("FFmpeg not available; using full file for language detection")
    else:
        logger.debug("Skipping language detection (either forced language or routing disabled)")
    
    # Step 2: Full transcription with the chosen language (if any)
    logger.info("Starting full transcription...")
    result = transcribe_full(
        client=client,
        audio_path=audio_path_obj,
        model=model,
        language=selected_lang,
        temperature=temperature
    )
    
    logger.debug("Enriching result metadata...")
    # Enrich metadata
    meta = result.setdefault("_meta", {})
    meta.update({
        "model": model,
        "detect_model": detect_model,
        "source_file": str(audio_path_obj),
        "forced_language": bool(language),
        "language_routing_enabled": language_routing,
        "routed_language": selected_lang if selected_lang else None,
        "probe_seconds": None if not use_probe else probe_seconds,
        "ffmpeg_used": ffmpeg_used,
    })
    
    logger.info("Transcription completed successfully")
    logger.debug(f"Result metadata: {meta}")
    
    return result
