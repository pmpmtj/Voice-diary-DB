"""
Path Utilities Package

This package provides cross-platform path handling utilities for the Google Drive
audio file downloader. It supports both regular Python execution and PyInstaller
frozen applications, ensuring consistent path resolution across different platforms.

Available Functions:
- resolve_path(): Resolve relative and absolute paths with base directory support
- ensure_directory(): Create directories and parent directories as needed
- get_script_directory(): Get script directory for both regular and frozen execution
- sanitize_filename(): Sanitize filenames for filesystem safety

Key Features:
- Cross-platform compatibility (Windows, macOS, Linux)
- PyInstaller frozen application support
- Relative and absolute path handling
- Directory creation and validation
- Filename sanitization for filesystem safety
- Script directory detection for both regular and frozen execution

Usage:
    from dl_src_gdrive.utils import resolve_path, ensure_directory, sanitize_filename
    
    # Resolve a relative path
    config_path = resolve_path("config/settings.json")
    
    # Ensure a directory exists
    log_dir = ensure_directory("logging/2024")
    
    # Sanitize a filename
    safe_name = sanitize_filename("My:File<Name>.mp3")

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

from .file_sys_utils import resolve_path, ensure_directory, get_script_directory, sanitize_filename

__all__ = [
    "resolve_path",
    "ensure_directory", 
    "get_script_directory",
    "sanitize_filename",
]
