"""
Path Utilities Module

This module provides cross-platform path handling utilities for the Google Drive
audio file downloader. It supports both regular Python execution and PyInstaller
frozen applications, ensuring consistent path resolution across different platforms.

Key Features:
- Cross-platform path resolution (Windows, macOS, Linux)
- PyInstaller frozen application support
- Relative and absolute path handling
- Directory creation and validation
- Filename sanitization for filesystem safety
- Script directory detection for both regular and frozen execution

The utilities handle:
- Path resolution with proper base directory handling
- Directory creation with parent directory support
- Script directory detection for frozen applications
- Filename sanitization to prevent filesystem issues

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import os
import sys
from pathlib import Path
from typing import Union, Optional


def resolve_path(path_input: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path, handling both relative and absolute paths.
    
    This function provides cross-platform path resolution that works consistently
    in both regular Python execution and PyInstaller frozen applications. It
    properly handles relative paths by resolving them against a base directory.
    
    The resolution process:
    1. Uses script directory as base if no base_dir provided
    2. Converts string inputs to Path objects
    3. Returns absolute paths as-is (resolved)
    4. Resolves relative paths against the base directory
    
    Args:
        path_input (Union[str, Path]): Input path as string or Path object
        base_dir (Optional[Path]): Base directory for relative paths.
                                 Defaults to script directory if None
        
    Returns:
        Path: Resolved Path object (always absolute)
        
    Raises:
        ValueError: If the path cannot be resolved due to invalid input
        
    Example:
        >>> resolve_path("config/settings.json")
        PosixPath('/path/to/script/config/settings.json')
        >>> resolve_path("/absolute/path/file.txt")
        PosixPath('/absolute/path/file.txt')
    """
    if base_dir is None:
        base_dir = get_script_directory()
    
    # Convert to Path object if needed
    if isinstance(path_input, str):
        path_input = Path(path_input)
    
    # Handle absolute paths
    if path_input.is_absolute():
        return path_input.resolve()
    
    # Handle relative paths
    resolved_path = (base_dir / path_input).resolve()
    
    return resolved_path


def ensure_directory(directory_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    This function creates a directory and all necessary parent directories
    if they don't exist. It's safe to call multiple times and won't raise
    an error if the directory already exists.
    
    The creation process:
    1. Converts input to Path object
    2. Checks if directory already exists
    3. Creates directory with all parent directories if needed
    4. Returns the Path object pointing to the directory
    
    Args:
        directory_path (Union[str, Path]): Path to the directory to ensure
        
    Returns:
        Path: Path object pointing to the ensured directory
        
    Raises:
        OSError: If the directory cannot be created due to permissions
                or filesystem issues
        
    Example:
        >>> ensure_directory("logging/2024/01")
        PosixPath('/path/to/logging/2024/01')
        >>> ensure_directory("/existing/directory")
        PosixPath('/existing/directory')
    """
    directory_path = Path(directory_path)
    
    if not directory_path.exists():
        directory_path.mkdir(parents=True, exist_ok=True)
    
    return directory_path


def get_script_directory() -> Path:
    """
    Get the directory containing the main script.
    
    This function provides reliable script directory detection for both regular
    Python execution and PyInstaller frozen applications. It ensures consistent
    behavior across different deployment scenarios.
    
    Detection logic:
    - For PyInstaller frozen apps: Uses sys.executable parent directory
    - For regular Python scripts: Uses __file__ parent directory
    
    Returns:
        Path: Path object pointing to the script directory
        
    Example:
        >>> get_script_directory()
        PosixPath('/path/to/script/directory')
        
    Note:
        This function is essential for resolving relative paths in the application,
        especially when running as a frozen executable or from different working
        directories.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # Running as regular Python script
        return Path(__file__).resolve().parent.parent

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing unsafe characters.
    
    This function ensures that a filename is safe for use on all major
    filesystems (Windows, macOS, Linux) by replacing or removing characters
    that could cause issues or security problems.
    
    The sanitization process:
    1. Replaces unsafe characters (< > : " / \ | ? *) with underscores
    2. Removes leading/trailing whitespace and dots
    3. Ensures filename is not empty (uses 'unnamed_file' if empty)
    4. Limits filename length to 255 characters (preserving extension)
    
    Args:
        filename (str): Original filename to sanitize
        
    Returns:
        str: Sanitized filename safe for filesystem use
        
    Example:
        >>> sanitize_filename("My:File<Name>.mp3")
        "My_File_Name_.mp3"
        >>> sanitize_filename("   .hidden_file   ")
        "hidden_file"
        >>> sanitize_filename("")
        "unnamed_file"
        
    Note:
        This function is essential for preventing filesystem errors when
        downloading files with potentially problematic names from Google Drive.
    """
    # Define unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    
    # Replace unsafe characters with underscores
    sanitized = filename
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    # Limit filename length (keep extension)
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        if ext:
            max_name_length = 255 - len(ext)
            sanitized = name[:max_name_length] + ext
        else:
            sanitized = sanitized[:255]
    
    return sanitized
