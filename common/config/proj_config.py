"""
Project Configuration Module

This module provides project-wide configuration settings that are used across
multiple modules in the GDrive transcription system.

Key Features:
- Centralized project configuration
- Environment variable support
- .env file fallback support
- Path validation and resolution
- Cross-module configuration sharing

Configuration Sources (in order of priority):
1. Environment variables (highest priority)
2. .env file (if python-dotenv is available)
3. Hardcoded defaults (lowest priority)

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectConfig:
    """
    Project-wide configuration settings.
    
    This class contains configuration values that are used across multiple
    modules in the project, such as file paths and directory settings.
    
    Attributes:
        download_dir (str): Default directory for audio file downloads
    """
    
    # Default values
    download_dir: str = r"C:\Users\pmpmt\Scripts_Cursor\pmpmtj_personal_diary\downloads"
    
    def __post_init__(self):
        """Load settings from environment variables and .env file."""
        # Load from environment variables first (highest priority)
        self.download_dir = os.getenv("DOWNLOAD_DIR", self.download_dir)
        
        # Fall back to .env file if environment variables not set
        try:
            from dotenv import load_dotenv
            # Load .env file from project root (two levels up from this file)
            project_root = Path(__file__).resolve().parent.parent.parent
            env_path = project_root / '.env'
            if env_path.exists():
                load_dotenv(env_path)
            
            # Re-check environment variables after loading .env
            self.download_dir = os.getenv("DOWNLOAD_DIR", self.download_dir)
        except ImportError:
            # python-dotenv not installed, continue with defaults/env vars
            pass
        
        # Validate download directory
        if self.download_dir:
            download_path = Path(self.download_dir)
            if not download_path.is_absolute():
                raise ValueError(f"DOWNLOAD_DIR must be an absolute path, got: {self.download_dir}")
    
    def get_download_dir(self) -> Path:
        """
        Get the download directory as a Path object.
        
        Returns:
            Path: Resolved download directory path
        """
        return Path(self.download_dir).expanduser().resolve()


# Global project configuration instance
PROJ_CONFIG = ProjectConfig()
