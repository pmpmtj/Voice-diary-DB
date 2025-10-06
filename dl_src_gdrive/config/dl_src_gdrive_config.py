"""
Application Configuration Module

This module provides centralized configuration management for the Google Drive
audio file downloader. It uses Python dataclasses to define configuration
structures with type hints and default values.

The configuration is organized into logical sections:
- GdriveConfig: Google Drive API settings and file processing options
- AppConfig: Main application configuration combining all sections

Configuration Features:
- Type-safe configuration with dataclasses
- Default values for all settings
- Centralized configuration management
- Easy to extend with new settings
- No external configuration files required

Usage:
    from config.dl_src_gdrive_config import CONFIG
    
    # Access Google Drive settings
    print(CONFIG.gdrive.allowed_audio_extensions)
    print(CONFIG.gdrive.allowed_text_extensions)
    
    # Modify settings at runtime
    CONFIG.gdrive.delete_audio_from_src = False
    CONFIG.gdrive.delete_text_from_src = True

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from common.config.proj_config import PROJ_CONFIG



@dataclass
class GdriveConfig:
    """
    Google Drive API and file processing configuration.
    
    This dataclass contains all configuration settings related to Google Drive
    operations, including API credentials, folder search settings, file processing
    options, and supported file formats for audio, text, and other file types.
    
    Configuration priority:
    1. Environment variables
    2. .env file
    3. Hardcoded defaults
    
    Attributes:
        delete_audio_from_src (bool): Whether to delete audio files from Google Drive after
                                     successful download. Default: False
        delete_text_from_src (bool): Whether to delete text files from Google Drive after
                                    successful download. Default: False
        delete_other_from_src (bool): Whether to delete other files from Google Drive after
                                     successful download. Default: False
        search_folders (List[str]): List of Google Drive folder IDs to search.
                                   Use "root" for root directory. Default: ["root"]
        client_secret_file (str): Filename of the OAuth2 client secret JSON file.
                                 Default: "client_secret.json"
        token_file (str): Path to store OAuth2 token file. Default: "config/token.json"
        scopes (List[str]): Google Drive API scopes. Default: ['https://www.googleapis.com/auth/drive']
        allowed_audio_extensions (List[str]): Audio file extensions to download.
                                             Default: ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.wma']
        allowed_text_extensions (List[str]): Text file extensions to download.
                                            Default: ['.txt', '.docx', '.pdf']
        allowed_other_extensions (List[str]): Other file extensions to download.
                                             Default: [] (empty list)
    """

    # Delete settings for different file types
    delete_audio_from_src: bool = False
    delete_text_from_src: bool = False
    delete_other_from_src: bool = False
    
    # Search and API settings
    search_folders: List[str] = field(default_factory=lambda: ["root"])
    client_secret_file: str = "dl_src_gdrive/config/client_secret.json"
    token_file: str = "dl_src_gdrive/config/token.json"
    scopes: List[str] = field(default_factory=lambda: ['https://www.googleapis.com/auth/drive'])
    
    # File extension settings
    allowed_audio_extensions: List[str] = field(default_factory=lambda: [
        '.mp3',   # MPEG Audio Layer III
        '.m4a',   # MPEG-4 Audio
        '.wav',   # Waveform Audio
        '.ogg',   # Ogg Vorbis
        '.flac',  # Free Lossless Audio Codec
        '.aac',   # Advanced Audio Coding
        '.wma',   # Windows Media Audio
    ])
    allowed_text_extensions: List[str] = field(default_factory=lambda: [
        '.txt',   # Plain text files
        '.docx',  # Microsoft Word documents
        '.pdf',   # Portable Document Format
    ])
    allowed_other_extensions: List[str] = field(default_factory=lambda: [])

    def __post_init__(self):
        """Load configuration from environment variables after initialization."""
        # Load delete settings from environment
        env_delete_audio = os.getenv('DELETE_AUDIO_FROM_SRC')
        if env_delete_audio is not None:
            self.delete_audio_from_src = env_delete_audio.lower() in ('true', '1', 'yes', 'on')
        
        env_delete_text = os.getenv('DELETE_TEXT_FROM_SRC')
        if env_delete_text is not None:
            self.delete_text_from_src = env_delete_text.lower() in ('true', '1', 'yes', 'on')
        
        env_delete_other = os.getenv('DELETE_OTHER_FROM_SRC')
        if env_delete_other is not None:
            self.delete_other_from_src = env_delete_other.lower() in ('true', '1', 'yes', 'on')
        
        # Backward compatibility: if old DELETE_FROM_SRC is set, apply to all types
        env_delete_legacy = os.getenv('DELETE_FROM_SRC')
        if env_delete_legacy is not None:
            delete_all = env_delete_legacy.lower() in ('true', '1', 'yes', 'on')
            self.delete_audio_from_src = delete_all
            self.delete_text_from_src = delete_all
            self.delete_other_from_src = delete_all
        
        # Load search_folders from environment (comma-separated)
        env_folders = os.getenv('SEARCH_FOLDERS')
        if env_folders:
            self.search_folders = [folder.strip() for folder in env_folders.split(',') if folder.strip()]
        
        # Load client_secret_file from environment
        env_client_secret = os.getenv('CLIENT_SECRET_FILE')
        if env_client_secret:
            self.client_secret_file = env_client_secret
        
        # Load token_file from environment
        env_token = os.getenv('TOKEN_FILE')
        if env_token:
            self.token_file = env_token
        
        # Load allowed_audio_extensions from environment (comma-separated)
        env_audio_extensions = os.getenv('ALLOWED_AUDIO_EXTENSIONS')
        if env_audio_extensions:
            self.allowed_audio_extensions = [ext.strip() for ext in env_audio_extensions.split(',') if ext.strip()]
        
        # Load allowed_text_extensions from environment (comma-separated)
        env_text_extensions = os.getenv('ALLOWED_TEXT_EXTENSIONS')
        if env_text_extensions:
            self.allowed_text_extensions = [ext.strip() for ext in env_text_extensions.split(',') if ext.strip()]
        
        # Load allowed_other_extensions from environment (comma-separated)
        env_other_extensions = os.getenv('ALLOWED_OTHER_EXTENSIONS')
        if env_other_extensions:
            self.allowed_other_extensions = [ext.strip() for ext in env_other_extensions.split(',') if ext.strip()]
    

@dataclass
class AppConfig:
    """
    Main application configuration combining all configuration sections.
    
    This is the top-level configuration class that combines all configuration
    sections into a single, easily accessible configuration object. It provides
    a centralized way to access all application settings.
    
    Attributes:
        gdrive (GdriveConfig): Google Drive API and file processing configuration.
                              Default: GdriveConfig() with default values
        download_dir (str): Absolute path to download directory for audio files.
                           Default: From PROJ_CONFIG.download_dir
    """
    # Google Drive configuration
    gdrive: GdriveConfig = field(default_factory=GdriveConfig)
    
    # Download directory configuration
    download_dir: str = PROJ_CONFIG.download_dir
    

# Global configuration instance
# Import this in your scripts: from dl_src_gdrive_config import CONFIG
CONFIG = AppConfig()


