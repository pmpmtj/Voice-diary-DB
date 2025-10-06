"""
Module-specific logging helper for dl_src_gdrive package.

This module provides a ready-to-use logger for the dl_src_gdrive package,
following the universal logging configuration pattern.

Usage:
    from .gdrive_logging import logger
    logger.info("Starting Google Drive download...")
    logger.debug("Detailed debug information")
    
    # Or get a custom logger
    from .gdrive_logging import get_logger
    custom_logger = get_logger("gdrive_downloader.custom_module")
"""

from common.logging_utils.logging_config import get_logger as _get_logger

# Module logger name
MODULE_LOGGER_NAME = "gdrive_downloader"

# Create the module logger
logger = _get_logger(MODULE_LOGGER_NAME)

# Export the get_logger function for custom loggers
def get_logger(logger_name: str = None, **kwargs):
    """
    Get a logger for the dl_src_gdrive package or a custom logger.
    
    Args:
        logger_name (str, optional): Custom logger name. If None, uses module logger.
        **kwargs: Additional arguments passed to the central get_logger function.
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> from .gdrive_logging import get_logger
        >>> custom_logger = get_logger("gdrive_downloader.file_processor")
        >>> custom_logger.info("Processing file...")
    """
    if logger_name is None:
        return logger
    
    # Ensure the logger name is prefixed with the module name
    if not logger_name.startswith(MODULE_LOGGER_NAME + "."):
        logger_name = f"{MODULE_LOGGER_NAME}.{logger_name}"
    
    return _get_logger(logger_name, **kwargs)

# Export the logger and get_logger function
__all__ = ['logger', 'get_logger']
