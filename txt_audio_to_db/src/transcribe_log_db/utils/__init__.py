"""
Utilities Package

This package provides utility modules for the transcription logging application.

Available Modules:
- path_utils: Cross-platform path handling utilities
- db_utils: Database connection and operation utilities

Available Functions:
- resolve_path(): Resolve relative and absolute paths with base directory support
- ensure_directory(): Create directories and parent directories as needed
- get_script_directory(): Get script directory for both regular and frozen execution
- sanitize_filename(): Sanitize filenames for filesystem safety
- get_db_manager(): Get a configured database manager instance
- get_transcription_ingestion(): Get a configured transcription ingestion handler

Key Features:
- Cross-platform compatibility (Windows, macOS, Linux)
- PyInstaller frozen application support
- Database connection management with PostgreSQL
- Path resolution and sanitization
- Transcription data ingestion with normalized schema
- Comprehensive error handling and logging

Usage:
    from transcribe_log_db.utils import resolve_path, get_db_manager, get_transcription_ingestion
    
    # Resolve a relative path
    config_path = resolve_path("config/settings.json")
    
    # Get database manager
    db_manager = get_db_manager()
    
    # Get transcription ingestion handler
    ingestion = get_transcription_ingestion()

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

from common.utils.file_sys_utils import resolve_path, ensure_directory, get_script_directory, sanitize_filename
from .db_utils import (
    DatabaseManager,
    TranscriptionIngestion,
    get_db_manager,
    get_transcription_ingestion
)
from .audio_finder import (
    get_default_audio_root,
    find_audio_candidates,
    filter_unprocessed,
    pick_newest,
)

__all__ = [
    # Path utilities
    "resolve_path",
    "ensure_directory", 
    "get_script_directory",
    "sanitize_filename",
    
    # Database utilities
    "DatabaseManager",
    "TranscriptionIngestion",
    "get_db_manager",
    "get_transcription_ingestion",
    
    # Audio discovery utilities
    "get_default_audio_root",
    "find_audio_candidates",
    "filter_unprocessed",
    "pick_newest",
]
