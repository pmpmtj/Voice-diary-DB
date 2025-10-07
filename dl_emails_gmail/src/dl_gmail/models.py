"""
Gmail Data Models

This module contains the data models for Gmail message processing.
It defines the structured data containers used throughout the application.

Key Features:
- MessageData: Complete email message information
- AttachmentData: Email attachment metadata
- Type hints and documentation
- Database-friendly structure

Usage:
    from src.dl_gmail.models import MessageData, AttachmentData
    
    msg_data = MessageData(message_id="123", thread_id="456", ...)
    attachment = AttachmentData(attachment_id="att123", filename="file.pdf")
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class AttachmentData:
    """
    Structured data container for email attachment information.
    
    This class holds attachment metadata extracted from Gmail messages
    in a format suitable for database storage.
    """
    attachment_id: str
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    file_path: Optional[str] = None
    download_status: str = "pending"  # pending, downloaded, failed


@dataclass
class MessageData:
    """
    Structured data container for Gmail message information.
    
    This class holds all the essential information extracted from a Gmail message
    in a format suitable for database storage and processing.
    """
    # Core identifiers
    message_id: str
    thread_id: str
    
    # Email metadata
    sender: str
    recipient: str
    subject: str
    date: str
    snippet: str
    
    # Content
    body_text: str
    body_html: Optional[str] = None
    
    # Attachments
    attachments: List[AttachmentData] = None
    attachment_count: int = 0
    
    # Processing metadata
    internal_date: Optional[str] = None
    size_estimate: Optional[int] = None
    label_ids: Optional[List[str]] = None
    
    # Processing status
    processed_successfully: bool = False
    label_applied: bool = False  # True if both "Processed" label added and "INBOX" label removed
    saved_to_db: bool = False  # True if message was successfully saved to database
    processing_timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.attachments is None:
            self.attachments = []
        if self.attachment_count == 0 and self.attachments:
            self.attachment_count = len(self.attachments)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return asdict(self)
