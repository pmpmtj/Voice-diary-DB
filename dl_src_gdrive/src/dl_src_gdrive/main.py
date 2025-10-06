#!/usr/bin/env python3
"""
Google Drive Audio File Downloader - Main CLI Script

This module provides the command-line interface for downloading audio files (MP3, M4A)
from Google Drive. It handles OAuth2 authentication, file discovery, and batch downloading
with comprehensive logging and error handling.

The script supports:
- Automatic authentication with Google Drive API
- Configurable folder search (root directory or specific folder IDs)
- Audio file filtering by extension (.mp3, .m4a)
- Optional file deletion from Google Drive after successful download
- Debug logging and credential cleanup options

Usage:
    python -m dl_src_gdrive.main [--cleanup] [--debug] [--delete-from-gdrive]

Examples:
    python -m dl_src_gdrive.main                    # Basic download
    python -m dl_src_gdrive.main --debug            # Enable debug logging
    python -m dl_src_gdrive.main --cleanup          # Remove credentials after download
    python -m dl_src_gdrive.main --delete-from-gdrive  # Delete files from Google Drive

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import argparse
import sys
from pathlib import Path

from .dl_gdrive_core.dl_src_gdrive import GoogleDriveDownloader
from common.logging_utils.logging_config import get_logger, set_console_level
from dl_src_gdrive.config.dl_src_gdrive_config import CONFIG


def main() -> int:
    """
    Main entry point for the Google Drive audio file downloader.
    
    This function handles command-line argument parsing, logger initialization,
    Google Drive authentication, file downloading, and result reporting.
    
    The process follows these steps:
    1. Parse command-line arguments (--debug, --cleanup, --delete-from-gdrive)
    2. Initialize logger with appropriate level
    3. Authenticate with Google Drive API
    4. Download all audio files from configured folders
    5. Report download results
    6. Optionally clean up credentials
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
        
    Raises:
        KeyboardInterrupt: If user interrupts the process (Ctrl+C)
        Exception: For any unexpected errors during execution
    """
    parser = argparse.ArgumentParser(
        description="Download audio, text, and other files from Google Drive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m dl_src_gdrive.main                    # Download all file types
    python -m dl_src_gdrive.main --skip-text        # Download only audio and other files
    python -m dl_src_gdrive.main --debug            # Enable debug logging
    python -m dl_src_gdrive.main --delete-audio     # Delete audio files after download
    python -m dl_src_gdrive.main --cleanup          # Remove credentials after download
        """
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove stored credentials after download (for security)'
    )
    
    # File type selection arguments
    parser.add_argument(
        '--skip-audio',
        action='store_true',
        help='Skip downloading audio files'
    )
    
    parser.add_argument(
        '--skip-text',
        action='store_true',
        help='Skip downloading text files'
    )
    
    parser.add_argument(
        '--skip-other',
        action='store_true',
        help='Skip downloading other files'
    )
    
    # Delete control arguments
    parser.add_argument(
        '--delete-audio',
        action='store_true',
        help='Delete audio files from Google Drive after successful download'
    )
    
    parser.add_argument(
        '--delete-text',
        action='store_true',
        help='Delete text files from Google Drive after successful download'
    )
    
    parser.add_argument(
        '--delete-other',
        action='store_true',
        help='Delete other files from Google Drive after successful download'
    )
    
    # Legacy argument for backward compatibility
    parser.add_argument(
        '--delete-from-gdrive',
        action='store_true',
        help='Delete all files from Google Drive after successful download (legacy, use --delete-audio/--delete-text/--delete-other instead)'
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = get_logger('gdrive_downloader')
    
    # Set debug level if requested
    if args.debug:
        set_console_level(logger, 'DEBUG')
        logger.debug("Debug logging enabled")
    
    # Override delete settings if command-line arguments are provided
    if args.delete_audio:
        CONFIG.gdrive.delete_audio_from_src = True
        logger.info("Delete audio files from Google Drive enabled via command-line argument")
    
    if args.delete_text:
        CONFIG.gdrive.delete_text_from_src = True
        logger.info("Delete text files from Google Drive enabled via command-line argument")
    
    if args.delete_other:
        CONFIG.gdrive.delete_other_from_src = True
        logger.info("Delete other files from Google Drive enabled via command-line argument")
    
    # Legacy support: if old --delete-from-gdrive is used, enable all delete settings
    if args.delete_from_gdrive:
        CONFIG.gdrive.delete_audio_from_src = True
        CONFIG.gdrive.delete_text_from_src = True
        CONFIG.gdrive.delete_other_from_src = True
        logger.info("Delete all files from Google Drive enabled via legacy --delete-from-gdrive argument")
    
    # Determine which file types to download
    download_audio = not args.skip_audio
    download_text = not args.skip_text
    download_other = not args.skip_other
    
    logger.info("=" * 60)
    logger.info("Google Drive File Downloader")
    logger.info("=" * 60)
    logger.info(f"Search folders: {CONFIG.gdrive.search_folders}")
    logger.info(f"Download audio files: {download_audio}")
    logger.info(f"Download text files: {download_text}")
    logger.info(f"Download other files: {download_other}")
    logger.info(f"Delete audio from source: {CONFIG.gdrive.delete_audio_from_src}")
    logger.info(f"Delete text from source: {CONFIG.gdrive.delete_text_from_src}")
    logger.info(f"Delete other from source: {CONFIG.gdrive.delete_other_from_src}")
    logger.info("=" * 60)
    
    try:
        # Initialize downloader
        logger.info("Initializing Google Drive downloader...")
        try:
            downloader = GoogleDriveDownloader()
        except FileNotFoundError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Please check that all required files exist and paths are correct.")
            return 1
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Please check your configuration settings.")
            return 1
        except Exception as e:
            logger.error(f"Failed to initialize downloader: {e}")
            return 1
        
        # Authenticate with Google Drive
        logger.info("Step 1: Authenticating with Google Drive...")
        try:
            if not downloader.authenticate():
                logger.error("Authentication failed. Please check your client secret file and internet connection.")
                logger.error("Make sure the client_secret.json file is valid and you have granted necessary permissions.")
                return 1
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            logger.error("Please check your Google Drive API credentials and network connection.")
            return 1
        
        # Download all files based on configuration
        logger.info("Step 2: Downloading files...")
        try:
            results = downloader.download_all_files(
                download_audio=download_audio,
                download_text=download_text,
                download_other=download_other
            )
        except Exception as e:
            logger.error(f"Download error: {e}")
            logger.error("Please check your Google Drive permissions and network connection.")
            return 1
        
        # Report results
        total_successful = sum(successful for successful, _ in results.values())
        total_files = sum(total for _, total in results.values())
        
        if total_files == 0:
            logger.warning("No files found in configured Google Drive folders")
            logger.info("Check your SEARCH_FOLDERS configuration if you expected to find files.")
        elif total_successful == total_files:
            logger.info(f"Successfully downloaded all {total_files} files")
        else:
            logger.warning(f"Downloaded {total_successful} out of {total_files} files")
            if total_successful < total_files:
                logger.warning("Some files failed to download. Check the logs for details.")
        
        # Cleanup credentials if requested
        if args.cleanup:
            logger.info("Step 3: Cleaning up credentials...")
            try:
                downloader.cleanup_credentials()
                logger.info("Credentials cleaned up for security")
            except Exception as e:
                logger.warning(f"Failed to cleanup credentials: {e}")
        
        logger.info("=" * 60)
        logger.info("Download process completed")
        logger.info("=" * 60)
        
        return 0 if total_successful == total_files else 1
        
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error("Please check the logs for more details and ensure all dependencies are installed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
