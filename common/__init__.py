"""
Common Utilities Package

This package provides shared utilities used across both the Google Drive downloader
and transcription/ingestion modules. It contains configuration management, path
utilities, and logging configuration that are common to both modules.

Key Features:
- Centralized configuration management
- Cross-platform path utilities
- Unified logging configuration
- Production-ready architecture

Usage:
    from common.config import PROJ_CONFIG
    from common.utils import resolve_path, ensure_directory
    from common.logging_utils import get_logger

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "[Your Name]"
