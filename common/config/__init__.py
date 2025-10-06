"""
Configuration Package

This package provides centralized configuration management for the entire pipeline.
It includes project-wide settings, database configuration, and Google Drive settings.

Available Modules:
- proj_config: Project-wide configuration (download directories, etc.)
- db_config: Database connection settings
- gdrive_config: Google Drive API settings

Usage:
    from common.config import PROJ_CONFIG
    from common.config.db_config import DB_CONFIG
    from common.config.gdrive_config import CONFIG
"""

from .proj_config import PROJ_CONFIG

__all__ = [
    "PROJ_CONFIG",
]
