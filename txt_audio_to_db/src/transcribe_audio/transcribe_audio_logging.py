"""
Module-specific logging helper for transcribe_audio package.

This module provides a ready-to-use logger for the transcribe_audio package,
following the universal logging configuration pattern.

Usage:
    from .transcribe_audio_logging import logger
    logger.info("Starting transcription...")
    logger.debug("Detailed debug information")
    
    # Or get a custom logger
    from .transcribe_audio_logging import get_logger
    custom_logger = get_logger("transcribe_audio.custom_module")
"""

import sys
from pathlib import Path

# Add the project root to the path to import logging_utils
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logging_utils.logging_config import get_logger as _get_logger

# Module logger name
MODULE_LOGGER_NAME = "transcribe_audio"

# Create the module logger
logger = _get_logger(MODULE_LOGGER_NAME)

# Export the get_logger function for custom loggers
def get_logger(logger_name: str = None, **kwargs):
    """
    Get a logger for the transcribe_audio package or a custom logger.
    
    Args:
        logger_name (str, optional): Custom logger name. If None, uses module logger.
        **kwargs: Additional arguments passed to the central get_logger function.
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> from .transcribe_audio_logging import get_logger
        >>> custom_logger = get_logger("transcribe_audio.transcription")
        >>> custom_logger.info("Processing audio...")
    """
    if logger_name is None:
        return logger
    
    # Ensure the logger name is prefixed with the module name
    if not logger_name.startswith(MODULE_LOGGER_NAME + "."):
        logger_name = f"{MODULE_LOGGER_NAME}.{logger_name}"
    
    return _get_logger(logger_name, **kwargs)

# Export commonly used logging functions for convenience
def debug(message: str, *args, **kwargs):
    """Log a debug message."""
    logger.debug(message, *args, **kwargs)

def info(message: str, *args, **kwargs):
    """Log an info message."""
    logger.info(message, *args, **kwargs)

def warning(message: str, *args, **kwargs):
    """Log a warning message."""
    logger.warning(message, *args, **kwargs)

def error(message: str, *args, **kwargs):
    """Log an error message."""
    logger.error(message, *args, **kwargs)

def critical(message: str, *args, **kwargs):
    """Log a critical message."""
    logger.critical(message, *args, **kwargs)

# Export the logger and get_logger function
__all__ = ['logger', 'get_logger', 'debug', 'info', 'warning', 'error', 'critical']
