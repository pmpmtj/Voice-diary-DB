"""
dl_gmail Application Configuration

This module contains all user-configurable settings for the dl_gmail automation tool.
Settings are organized into logical sections using dataclasses for better IDE support and type safety.

Note: Logging configuration is handled by the universal logging system in logging_utils/logging_config.py

Usage:
    from config.dl_gmail_config import CONFIG
    search_query = CONFIG.gmail.search_query
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GmailConfig:
    """Gmail API and email processing configuration."""
    
    # Gmail search query to find emails to process
    # Examples: "in:inbox -label:Processed", "from:example@company.com", "subject:urgent"
    search_query: str = "in:inbox -label:Processed"
    
    # Label name to apply to processed emails (prevents reprocessing)
    processed_label: str = "Processed"
    
    # Maximum number of emails to process in a single run
    # Higher values = more emails per run, but longer processing time
    max_per_run: int = 50
        
    # Sender email filtering - only process emails from these senders
    # Supports wildcards: "*@company.com", "boss@*", "exact@email.com"
    # Empty list = no filtering (process all senders)
    # Examples: ["*@company.com", "boss@*", "urgent@domain.com"]
    allowed_senders: List[str] = field(default_factory=lambda: [
        "pmpmtj@gmail.com",  # Specific Gmail address
        #"*@google.com",       # All emails from Google domain
        "scms.manu@gmail.com",
        "*@gmail.com",
        "pmpmtj@*",
        "pjhq2025@*"
    ])
    
    # Inbox cleanup - remove processed emails from inbox view
    # True = emails disappear from inbox after processing (clean inbox)
    # False = emails remain in inbox after processing
    # Emails are always accessible via "Processed" label regardless of this setting
    clean_inbox: bool = True
    
    # Attachment download configuration
    # Enable/disable downloading of email attachments
    download_attachments: bool = True
    
    # Directory to save downloaded attachments (absolute path)
    # Create subdirectories by date (YYYY-MM-DD) for organization
    # Example: C:\Users\pmpmt\Downloads\gmail_attachments\2025-10-05\
    attachment_download_dir: str = r"C:\Users\pmpmt\Downloads\gmail_attachments"
    
    # Maximum attachment file size to download (in bytes)
    # Large files will be skipped and logged as warnings
    # 10 MB = 10 * 1024 * 1024 bytes
    max_attachment_size: int = 10 * 1024 * 1024  # 10 MB
    
    # Handle duplicate filenames by adding counter suffix
    # True = "document.pdf", "document_1.pdf", "document_2.pdf"
    # False = Overwrite existing files (not recommended)
    handle_duplicate_filenames: bool = True


@dataclass
class AlertsConfig:
    """Email alert configuration for error notifications."""
    
    # Enable/disable email alerts when processing fails
    enabled: bool = True
    
    # Email address to send alerts to
    # Must be a Gmail address that the script has access to
    to_email: str = "<pjhq2025@gmail.com>"


@dataclass
class AuthConfig:
    """Google API authentication configuration."""
    
    # Path to Google OAuth2 credentials file (JSON)
    # Download from Google Cloud Console > APIs & Services > Credentials
    credentials_file: str = "common/config/google_account/client_secret.json"
    
    # Path to store OAuth2 tokens (auto-generated)
    # Tokens are refreshed automatically when they expire
    token_file: str = "common/config/google_account/token.json"


@dataclass
class AppConfig:
    """Main application configuration combining all sections."""
    
    # Gmail configuration
    gmail: GmailConfig = field(default_factory=GmailConfig)
    
    # Alert configuration
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    
    # Authentication configuration
    auth: AuthConfig = field(default_factory=AuthConfig)


# Global configuration instance
# Import this in your scripts: from app_config import CONFIG
CONFIG = AppConfig()


