"""
Google Drive Downloader Package

This package provides functionality for downloading audio files from Google Drive
and integrating with the transcription and database logging system.
"""

from .dl_gdrive_core.dl_src_gdrive import GoogleDriveDownloader
from .main import main
from .gdrive_logging import logger, get_logger

__all__ = [
    "GoogleDriveDownloader",
    "main",
    "logger",
    "get_logger",
]