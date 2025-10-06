#!/usr/bin/env python3
"""
CLI: Transcribe an audio file (MP3/M4A/WAV) with OpenAI and output JSON,
     with optional language routing (probe first N seconds, then transcribe).

Usage:
  python -m src.transcribe_audio.cli.transcribe_cli input.m4a
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --out transcript.json
  python -m src.transcribe_audio.cli.transcribe_cli input.wav --probe-seconds 15
  python -m src.transcribe_audio.cli.transcribe_cli input.m4a --no-probe                     # skip ffmpeg probe
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --language pt                  # bypass auto, force Portuguese
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --language-routing             # enable keyword-based language routing
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --model gpt-4o-mini-transcribe
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --debug                        # enable debug logging
  python -m src.transcribe_audio.cli.transcribe_cli input.mp3 --log-dir ./my_logs           # custom log directory

Exit codes:
  0 = success
  1 = usage / argument issue
  2 = file not found / unsupported type
  3 = API error (network/auth/model/etc.)
  4 = ffmpeg error (non-fatal: we will fallback automatically)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict

# ============================================================================
# Initialize paths - handling both frozen (PyInstaller) and regular Python execution
# ============================================================================
if getattr(sys, 'frozen', False):
    # Running as compiled executable (e.g., PyInstaller)
    SCRIPT_DIR = Path(sys.executable).parent
else:
    # Running as regular Python script
    SCRIPT_DIR = Path(__file__).resolve().parent

from txt_audio_to_db.config.transcribe_audio_config import TranscriptionConfig
from ..core import transcribe_audio
import sys
from pathlib import Path

# Add the project root to the path to import logging_utils
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..transcribe_audio_logging import get_logger
from common.logging_utils.logging_config import set_console_level

def disable_file_logging(logger):
    """Disable file logging by removing file handlers from the logger."""
    import logging
    # Remove all file handlers (handlers that are not StreamHandler with stdout)
    handlers_to_remove = []
    for handler in logger.handlers:
        if not (isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stdout>'):
            handlers_to_remove.append(handler)
    
    for handler in handlers_to_remove:
        logger.removeHandler(handler)


def die(msg: str, code: int) -> "NoReturn":  # type: ignore[name-defined]
    """Print error message and exit with specified code."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    # Get defaults from config
    default_model = TranscriptionConfig.get_main_model()
    default_detect_model = TranscriptionConfig.get_probe_model()
    default_temperature = TranscriptionConfig.get_default('temperature')
    default_probe_seconds = TranscriptionConfig.get_default('probe_seconds')
    default_language_routing = TranscriptionConfig.get_default('language_routing')
    default_log_dir = TranscriptionConfig.get_log_dir()
    
    p = argparse.ArgumentParser(description="Transcribe audio to JSON via OpenAI with optional language routing.")
    p.add_argument("audio_path", nargs='?', help="Path to .mp3, .m4a, or .wav file (required unless --stdin is used)")
    p.add_argument("--model", default=default_model, help=f"Main transcription model (default: {default_model})")
    p.add_argument("--detect-model", default=default_detect_model, help=f"Probe model for language detection (default: {default_detect_model})")
    p.add_argument("--language", default=None, help="ISO-639-1 code to force (e.g., 'en', 'pt'); omit to auto-detect")
    p.add_argument("--probe-seconds", type=int, default=default_probe_seconds, help=f"Seconds to sample for language detection (default: {default_probe_seconds})")
    p.add_argument("--no-probe", action="store_true", help="Disable ffmpeg sampling; fallback to API-only language detection")
    p.add_argument("--language-routing", action="store_true", default=default_language_routing, 
                   help="Enable keyword-based language routing (default: disabled, Whisper auto-detects)")
    p.add_argument("--out", default=None, help="Optional output .json path; prints to stdout if omitted")
    p.add_argument("--temperature", type=float, default=default_temperature, help=f"Decoding temperature (default: {default_temperature})")
    p.add_argument("--debug", action="store_true", help="Enable DEBUG level logging to console (default: INFO)")
    p.add_argument("--log-dir", default=default_log_dir, help=f"Directory for log files (default: {default_log_dir})")
    p.add_argument("--enable-file-logging", action="store_true", help="Enable logging to files (disabled by default)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making API calls (useful for cost estimation)")
    p.add_argument("--stdin", action="store_true", help="Read file paths from stdin (one per line) for batch processing")
    
    args = p.parse_args()
    
    # Validate that either audio_path or --stdin is provided
    if not args.audio_path and not args.stdin:
        p.error("Either audio_path or --stdin must be provided")
    
    return args


def ensure_api_key():
    """Ensure OpenAI API key is set."""
    if not os.getenv("OPENAI_API_KEY"):
        die("OPENAI_API_KEY is not set. Set it and retry.", TranscriptionConfig.EXIT_CODES['usage_error'])


def setup_logging_from_args(args) -> 'logging.Logger':
    """
    Initialize logging based on CLI arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Configured logger instance
    """
    log_dir = Path(args.log_dir) if args.enable_file_logging else None
    console_level = 'DEBUG' if args.debug else 'INFO'
    
    # Create logger for CLI
    logger = get_logger(
        'transcribe_cli',
        log_dir=log_dir,
        console_level=console_level,
    )
    
    # Disable file logging if not requested
    if not args.enable_file_logging:
        disable_file_logging(logger)
    
    logger.debug(f"CLI started with arguments: {vars(args)}")
    logger.debug(f"Script directory: {SCRIPT_DIR}")
    logger.debug(f"Logging level: {console_level}")
    
    return logger


def create_dry_run_result(args, logger) -> Dict:
    """
    Create a dry-run result showing what would be done without API calls.
    
    Args:
        args: Parsed command-line arguments
        logger: Logger instance for output
        
    Returns:
        Mock transcription result dictionary
    """
    from pathlib import Path
    from txt_audio_to_db.config.transcribe_audio_config import TranscriptionConfig
    
    # Validate file exists (same as real transcription)
    audio_path_obj = Path(args.audio_path).expanduser().resolve()
    if not audio_path_obj.exists() or not audio_path_obj.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path_obj}")
    
    if not TranscriptionConfig.is_extension_allowed(audio_path_obj.suffix):
        allowed = ', '.join(sorted(TranscriptionConfig.ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{audio_path_obj.suffix}'. Use: {allowed}")
    
    # Check FFmpeg availability
    from ..core.language_detection import have_ffmpeg
    ffmpeg_available = have_ffmpeg()
    
    # Determine what would happen
    would_use_probe = args.language_routing and not args.language and not args.no_probe and ffmpeg_available
    would_detect_language = args.language_routing and not args.language
    
    logger.info(f"File validation: OK {audio_path_obj.name} ({audio_path_obj.suffix})")
    logger.info(f"FFmpeg available: {'YES' if ffmpeg_available else 'NO'}")
    logger.info(f"Would use probe slice: {'YES' if would_use_probe else 'NO'}")
    logger.info(f"Would detect language: {'YES' if would_detect_language else 'NO'}")
    logger.info(f"API calls that would be made:")
    if would_detect_language:
        logger.info(f"  - Language detection: {args.detect_model} (probe: {would_use_probe})")
    logger.info(f"  - Main transcription: {args.model}")
    
    # Create mock result
    result = {
        "text": "[DRY RUN] This is a mock transcription result. No API calls were made.",
        "language": args.language or "auto-detect",
        "_meta": {
            "model": args.model,
            "detect_model": args.detect_model,
            "source_file": str(audio_path_obj),
            "forced_language": bool(args.language),
            "language_routing_enabled": args.language_routing,
            "routed_language": None,  # Would be determined by actual detection
            "probe_seconds": None if args.no_probe else args.probe_seconds,
            "ffmpeg_used": would_use_probe,
            "dry_run": True,
            "ffmpeg_available": ffmpeg_available,
        }
    }
    
    return result


def process_stdin_batch(args, logger) -> None:
    """
    Process multiple files from stdin input.
    
    Args:
        args: Parsed command-line arguments
        logger: Logger instance for output
    """
    import sys
    
    logger.info("Processing files from stdin...")
    
    # Read file paths from stdin
    file_paths = []
    try:
        for line in sys.stdin:
            file_path = line.strip()
            if file_path and not file_path.startswith('#'):  # Skip empty lines and comments
                file_paths.append(file_path)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return
    
    if not file_paths:
        logger.warning("No file paths provided via stdin")
        return
    
    logger.info(f"Found {len(file_paths)} files to process")
    
    # Process each file
    success_count = 0
    error_count = 0
    
    for i, file_path in enumerate(file_paths, 1):
        logger.info(f"Processing file {i}/{len(file_paths)}: {file_path}")
        
        try:
            # Create args for this specific file
            file_args = argparse.Namespace(**vars(args))
            file_args.audio_path = file_path
            file_args.out = None  # Force stdout output for batch mode
            
            # Process the file
            result = perform_transcription(file_args, logger)
            
            # Output result as JSON line
            output = json.dumps(result, ensure_ascii=False, separators=(',', ':'))
            print(output)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to process {file_path}: {e}")
            
            # Output error as JSON line
            error_result = {
                "error": str(e),
                "file": file_path,
                "success": False
            }
            output = json.dumps(error_result, ensure_ascii=False, separators=(',', ':'))
            print(output)
    
    logger.info(f"Batch processing complete: {success_count} successful, {error_count} errors")


def perform_transcription(args, logger) -> Dict:
    """
    Perform the transcription based on CLI arguments.
    
    Args:
        args: Parsed command-line arguments
        logger: Logger instance for output
        
    Returns:
        Transcription result dictionary
        
    Raises:
        ImportError: If OpenAI SDK not installed
        FileNotFoundError: If audio file not found
        ValueError: If file type not supported
        Exception: For API and other errors
    """
    logger.info(f"Starting transcription of: {args.audio_path}")
    logger.debug(f"Model: {args.model}, Detect model: {args.detect_model}")
    logger.debug(f"Temperature: {args.temperature}, Probe seconds: {args.probe_seconds}")
    logger.debug(f"Language routing: {args.language_routing}, Forced language: {args.language}")
    logger.debug(f"Use probe: {not args.no_probe}")
    
    # Handle dry-run mode
    if args.dry_run:
        logger.info("DRY RUN MODE - No API calls will be made")
        return create_dry_run_result(args, logger)
    
    # Use the core transcription functionality
    result = transcribe_audio(
        audio_path=args.audio_path,
        model=args.model,
        detect_model=args.detect_model,
        language=args.language,
        probe_seconds=args.probe_seconds,
        use_probe=(not args.no_probe),
        language_routing=args.language_routing,
        temperature=args.temperature
    )
    
    logger.debug("Transcription completed successfully")
    return result


def log_language_detection_info(args, result, logger) -> None:
    """
    Log information about language detection results.
    
    Args:
        args: Parsed command-line arguments
        result: Transcription result dictionary
        logger: Logger instance for output
    """
    meta = result.get("_meta", {})
    
    if args.language_routing and not args.language:
        detected = meta.get("routed_language")
        ffmpeg_used = meta.get("ffmpeg_used", False)
        
        if detected:
            logger.info(f"Language routing enabled: detected '{detected}'")
        else:
            logger.info("Language routing enabled but detection failed; Whisper will auto-detect.")
        
        # Surface FFmpeg status to user
        if ffmpeg_used:
            logger.info("FFmpeg probe slice used for fast language detection")
        else:
            logger.info("FFmpeg not available; using full file for language detection")
    elif not args.language:
        logger.info("Language routing disabled; Whisper will auto-detect language.")


def output_transcription_result(result, output_path, logger) -> None:
    """
    Output transcription result to file or stdout.
    
    Args:
        result: Transcription result dictionary
        output_path: Optional output file path (None for stdout)
        logger: Logger instance for output
    """
    logger.debug("Preparing output...")
    output = json.dumps(result, ensure_ascii=False, indent=2)
    
    if output_path:
        out_path = Path(output_path).expanduser().resolve()
        logger.debug(f"Writing output to: {out_path}")
        out_path.write_text(output, encoding="utf-8")
        logger.info(f"Wrote JSON transcription to: {out_path}")
    else:
        logger.debug("Writing output to stdout")
        print(output)


def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Initialize logging
    logger = setup_logging_from_args(args)
    
    # Try to load .env file if it exists
    logger.debug("Checking for .env file...")
    env_loaded = TranscriptionConfig.load_env_file()
    if env_loaded:
        logger.debug("Loaded environment variables from .env file")
    else:
        logger.debug("No .env file found or failed to load")
    
    # Validate environment
    logger.debug("Checking for OPENAI_API_KEY...")
    ensure_api_key()
    logger.debug("API key found")

    # Handle stdin batch processing
    if args.stdin:
        try:
            process_stdin_batch(args, logger)
            logger.info("Batch processing completed successfully")
            return
        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=args.debug)
            die(f"Batch processing failed: {e}", TranscriptionConfig.EXIT_CODES['api_error'])

    # Single file processing
    try:
        # Perform transcription
        result = perform_transcription(args, logger)
        
        # Log language detection info
        log_language_detection_info(args, result, logger)

    except (ImportError, FileNotFoundError, ValueError) as e:
        # Handle known errors with appropriate exit codes
        if isinstance(e, ImportError):
            logger.error(f"Import error: {e}")
            die(str(e), TranscriptionConfig.EXIT_CODES['usage_error'])
        elif isinstance(e, FileNotFoundError):
            logger.error(f"File not found: {e}")
            die(str(e), TranscriptionConfig.EXIT_CODES['file_error'])
        elif isinstance(e, ValueError):
            logger.error(f"Value error: {e}")
            die(str(e), TranscriptionConfig.EXIT_CODES['file_error'])
    except Exception as e:
        # Handle API and other errors
        logger.error(f"Transcription failed: {e}", exc_info=args.debug)
        die(f"Transcription request failed: {e}", TranscriptionConfig.EXIT_CODES['api_error'])

    # Output results
    output_transcription_result(result, args.out, logger)
    
    logger.info("Transcription process completed successfully")
    logger.debug("Exiting with success code")


if __name__ == "__main__":
    main()

