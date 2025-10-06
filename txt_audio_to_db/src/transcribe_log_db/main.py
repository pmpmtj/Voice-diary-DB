"""
Main Application Entry Point

This module provides the main entry point for the transcription logging application.
It demonstrates how to initialize the database and ingest transcription responses
into the normalized schema.

Key Features:
- Database initialization with schema creation
- Transcription ingestion from JSON responses
- Command-line interface for testing and demonstration
- Comprehensive logging and error handling

Usage:
    python -m transcribe_log_db.main
    
    Or with a JSON file:
    python -m transcribe_log_db.main --input example_output.json

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from common.logging_utils.logging_config import get_logger
from .utils.db_utils import get_db_manager, get_transcription_ingestion
from .utils import (
    get_default_audio_root,
    find_audio_candidates,
    filter_unprocessed,
    pick_newest,
)
from .utils.text_finder import (
    get_default_text_root,
    find_text_candidates,
    filter_unprocessed as filter_unprocessed_text,
    pick_newest as pick_newest_text,
)
from .utils.text_ingestion import get_text_ingestion

# Optional import of transcriber; we only use when --audio is provided
try:
    from ..transcribe_audio.core.transcription import transcribe_audio  # type: ignore
except Exception:  # pragma: no cover
    transcribe_audio = None


def initialize_database(db_manager) -> None:
    """
    Initialize the database with the schema.
    
    Args:
        db_manager: Database manager instance
    """
    logger = get_logger("main")
    logger.info("Initializing database...")
    
    try:
        db_manager.initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def ingest_from_file(ingestion_handler, file_path: Path, 
                    title: Optional[str] = None,
                    mood: Optional[str] = None,
                    tags: Optional[list] = None) -> dict:
    """
    Ingest transcription data from a JSON file.
    
    Args:
        ingestion_handler: Transcription ingestion handler
        file_path (Path): Path to the JSON file
        title (Optional[str]): Diary entry title
        mood (Optional[str]): Diary entry mood
        tags (Optional[list]): Diary entry tags
        
    Returns:
        dict: Result of the ingestion process
    """
    logger = get_logger("main")
    logger.info(f"Loading transcription data from: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    # Load and parse the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        response_data = json.load(f)
    
    logger.info("Transcription data loaded successfully")
    
    # Ingest the data
    result = ingestion_handler.ingest_transcription(
        response_data, title=title, mood=mood, tags=tags
    )
    
    return result


def _process_text_documents(args, logger) -> dict:
    """
    Process text documents (txt, docx, pdf) and return the last result.
    
    Args:
        args: Command line arguments
        logger: Logger instance
        
    Returns:
        dict: Result of the last processed text document
    """
    text_ingestion_handler = get_text_ingestion()
    
    # Discover text files
    text_root = args.audio_dir or get_default_text_root()
    logger.info(f"Discovering text documents under: {text_root}")
    text_candidates = find_text_candidates(text_root, one_level=True)
    logger.debug(f"Found {len(text_candidates)} candidate text files")
    
    if text_candidates:
        to_process_text = text_candidates
        if not args.reprocess:
            with get_db_manager().get_connection() as conn:
                to_process_text = filter_unprocessed_text(conn, text_candidates)
            logger.info(f"Unprocessed text files: {len(to_process_text)}")
        
        if to_process_text:
            if not args.batch:
                newest_text = pick_newest_text(to_process_text)
                to_process_text = [newest_text] if newest_text else []
                logger.info(f"Selected newest text document: {newest_text}")
            
            # Process text documents
            text_results = []
            for text_path in to_process_text:
                try:
                    logger.info(f"Processing text document: {text_path}")
                    text_result = text_ingestion_handler.ingest_text_document(
                        text_path,
                        mood=args.mood,
                        tags=args.tags
                    )
                    text_results.append(text_result)
                    logger.info(f"Text document processed successfully: {text_result}")
                except Exception as e:
                    logger.error(f"Failed to process text document {text_path}: {e}")
                    # Continue processing other files
                    continue
            
            if text_results:
                logger.info(f"Processed {len(text_results)} text documents successfully")
                # Return the last result for display
                return text_results[-1]
            else:
                logger.warning("No text documents were processed successfully")
                return {"diary_id": None, "source_file_id": None, "run_id": None, "usage_id": None}
        else:
            logger.info("No unprocessed text documents found")
            return {"diary_id": None, "source_file_id": None, "run_id": None, "usage_id": None}
    else:
        logger.info("No text documents found to process")
        return {"diary_id": None, "source_file_id": None, "run_id": None, "usage_id": None}


def ingest_sample_data(ingestion_handler) -> dict:
    """
    Ingest sample transcription data for demonstration.
    
    Args:
        ingestion_handler: Transcription ingestion handler
        
    Returns:
        dict: Result of the ingestion process
    """
    logger = get_logger("main")
    logger.info("Ingesting sample transcription data")
    
    # Sample data based on the example_output.json structure
    sample_data = {
        "text": "Alô, alô, isto é um teste de gravação em português. Obrigado pela atenção.",
        "logprobs": None,
        "usage": {
            "input_tokens": 126,
            "output_tokens": 23,
            "total_tokens": 149,
            "type": "tokens",
            "input_token_details": {
                "audio_tokens": 126,
                "text_tokens": 0
            }
        },
        "_meta": {
            "model": "gpt-4o-transcribe",
            "detect_model": "gpt-4o-mini-transcribe",
            "source_file": "C:\\Users\\pmpmt\\Scripts_Cursor\\251002-1-Transcribe_audio\\audio-transcriber\\input.m4a",
            "forced_language": False,
            "language_routing_enabled": False,
            "routed_language": None,
            "probe_seconds": 25,
            "ffmpeg_used": False
        }
    }
    
    # Ingest the sample data
    result = ingestion_handler.ingest_transcription(
        sample_data,
        title="Sample Portuguese Transcription",
        mood="test",
        tags=["sample", "portuguese", "test"]
    )
    
    logger.info("Sample data ingestion completed")
    return result


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Transcription Logging Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Initialize database and ingest sample data
    python -m transcribe_log_db.main
    
    # Ingest from a specific JSON file
    python -m transcribe_log_db.main --input example_output.json
    
    # Ingest with custom metadata
    python -m transcribe_log_db.main --input data.json --title "My Recording" --mood "happy"
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=Path,
        help='Path to JSON file containing transcription response'
    )
    
    parser.add_argument(
        '--title',
        type=str,
        help='Title for the diary entry'
    )
    
    parser.add_argument(
        '--mood',
        type=str,
        help='Mood for the diary entry'
    )
    
    parser.add_argument(
        '--tags',
        nargs='+',
        help='Tags for the diary entry (space-separated)'
    )
    
    parser.add_argument(
        '--init-only',
        action='store_true',
        help='Only initialize the database, do not ingest data'
    )
    
    parser.add_argument(
        '--audio-dir',
        type=Path,
        help='Override default audio root (defaults to PROJ_CONFIG.download_dir)'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process all unprocessed audio files instead of just the newest one'
    )
    
    parser.add_argument(
        '--reprocess',
        action='store_true',
        help='Ignore DB check and reprocess audio even if already processed'
    )
    
    parser.add_argument(
        '--audio', '-a',
        type=Path,
        help='Path to an audio file to transcribe first, then ingest'
    )
    
    parser.add_argument(
        '--text-only',
        action='store_true',
        help='Skip audio processing and only process text documents'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = get_logger("main")
    logger.info("Starting transcription logging application")
    
    try:
        # Initialize database manager
        db_manager = get_db_manager()
        logger.info("Database manager initialized")
        
        # Initialize database schema
        initialize_database(db_manager)
        
        if args.init_only:
            logger.info("Database initialization completed. Exiting.")
            return
        
        # Initialize ingestion handler
        ingestion_handler = get_transcription_ingestion()
        logger.info("Transcription ingestion handler initialized")
        
        # Initialize result variable
        result = None
        
        # Process based on mode
        if args.text_only:
            # Text-only mode: skip audio processing
            logger.info("Text-only mode: skipping audio processing")
            result = _process_text_documents(args, logger)
        elif args.audio:
            if transcribe_audio is None:
                raise ImportError("transcribe_audio package is not available. Install or ensure it's on PYTHONPATH.")
            logger.info(f"Transcribing audio file: {args.audio}")
            # Run transcription to produce the JSON-like dict
            tr_result = transcribe_audio(str(args.audio))
            logger.info("Transcription completed, ingesting result")
            result = ingestion_handler.ingest_transcription(
                tr_result,
                title=args.title,
                mood=args.mood,
                tags=args.tags
            )
        elif not args.input:
            # No explicit JSON input and no explicit --audio; discover from default dir
            if transcribe_audio is None:
                raise ImportError("transcribe_audio package is not available. Install or ensure it's on PYTHONPATH.")
            root = args.audio_dir or get_default_audio_root()
            logger.info(f"Discovering audio under: {root}")
            candidates = find_audio_candidates(root, one_level=True)
            logger.debug(f"Found {len(candidates)} candidate audio files")
            to_process = candidates
            if not args.reprocess:
                with get_db_manager().get_connection() as conn:
                    to_process = filter_unprocessed(conn, candidates)
                logger.info(f"Unprocessed audio files: {len(to_process)}")
            if not to_process:
                logger.info("No unprocessed audio files found, continuing to text processing...")
                last_result = None
            else:
                if not args.batch:
                    newest = pick_newest(to_process)
                    to_process = [newest] if newest else []
                    logger.info(f"Selected newest audio: {newest}")

                # Process one or many
                last_result = None
                for audio_path in to_process:
                    logger.info(f"Transcribing: {audio_path}")
                    tr_result = transcribe_audio(str(audio_path))
                    # Save transcript JSON next to audio
                    try:
                        out_dir = Path(audio_path).parent
                        out_file = out_dir / "transcript.json"
                        if out_file.exists():
                            from datetime import datetime
                            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                            out_file = out_dir / f"transcript-{ts}.json"
                        with open(out_file, 'w', encoding='utf-8') as f:
                            import json as _json
                            _json.dump(tr_result, f, ensure_ascii=False, indent=2)
                        logger.info(f"Saved transcript: {out_file}")
                    except Exception as e:
                        logger.warning(f"Failed to save transcript JSON: {e}")

                    last_result = ingestion_handler.ingest_transcription(
                        tr_result,
                        title=args.title,
                        mood=args.mood,
                        tags=args.tags
                    )
                result = last_result
        elif args.input:
            # Ingest from specified file
            result = ingest_from_file(
                ingestion_handler, 
                args.input,
                title=args.title,
                mood=args.mood,
                tags=args.tags
            )
        else:
            # Ingest sample data
            result = ingest_sample_data(ingestion_handler)
        
        # Process text documents (in normal mode, after audio processing)
        if not args.text_only and not args.audio and not args.input:
            # Normal mode: process text after audio
            logger.info("Starting text document processing...")
            _process_text_documents(args, logger)
        
        # Display results
        logger.info("Ingestion completed successfully!")
        print("\n=== Ingestion Results ===")
        if result:
            print(f"Diary ID: {result['diary_id']}")
            print(f"Source File ID: {result['source_file_id']}")
            print(f"Transcription Run ID: {result['run_id']}")
            print(f"Usage ID: {result['usage_id']}")
        else:
            print("No files were processed (all files were already processed)")
        print("========================\n")
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)
    
    logger.info("Application completed successfully")


if __name__ == "__main__":
    main()
