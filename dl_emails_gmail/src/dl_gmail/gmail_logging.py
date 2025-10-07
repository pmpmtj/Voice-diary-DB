"""
Module-specific logging helper for dl_gmail package.

This module provides a ready-to-use logger for the dl_gmail package,
following the universal logging configuration pattern.

Usage:
    from .logging import logger
    logger.info("Starting Gmail download...")
    logger.debug("Detailed debug information")
    
    # Or get a custom logger
    from .logging import get_logger
    custom_logger = get_logger("dl_gmail.custom_module")
"""

from common.logging_utils.logging_config import get_logger as _get_logger

# Module logger name
MODULE_LOGGER_NAME = "dl_gmail"

# Create the module logger
logger = _get_logger(MODULE_LOGGER_NAME)

# Export the get_logger function for custom loggers
def get_logger(logger_name: str = None, **kwargs):
    """
    Get a logger for the dl_gmail package or a custom logger.
    
    Args:
        logger_name (str, optional): Custom logger name. If None, uses module logger.
        **kwargs: Additional arguments passed to the central get_logger function.
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> from .logging import get_logger
        >>> custom_logger = get_logger("dl_gmail.email_processor")
        >>> custom_logger.info("Processing email...")
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
