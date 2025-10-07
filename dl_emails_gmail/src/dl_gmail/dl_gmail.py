"""
Gmail Downloader Core Module

This module provides the core functionality for downloading and processing Gmail messages.
It fetches messages matching the configured search query, extracts structured data,
and marks successfully processed messages with a "Processed" label.

Key Features:
- Fetches all messages matching CONFIG.gmail.search_query
- Extracts structured data suitable for database storage
- Applies "Processed" label and removes "INBOX" label for clean inbox
- Continues processing even if label operations fail
- Designed for import by other system components

Usage:
    from src.dl_gmail.dl_gmail import process_gmail_messages, MessageData
    
    # Process messages and get structured data
    processed_messages = process_gmail_messages()
    for msg_data in processed_messages:
        print(f"Processed: {msg_data.subject} from {msg_data.sender}")
"""

import base64
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from dl_emails_gmail.config.dl_gmail_config import CONFIG
from .gmail_client import (
    build_gmail_service, 
    list_messages, 
    get_message, 
    get_message_headers,
    apply_label_to_message,
    apply_and_remove_labels,
    download_attachment
)
from .gmail_logging import logger, info, debug, error, warning
from .models import MessageData, AttachmentData
from .db_persistence import save_message_to_db


def convert_unix_timestamp_to_datetime(unix_timestamp: str) -> Optional[str]:
    """
    Convert Unix timestamp string to ISO datetime format.
    
    Args:
        unix_timestamp (str): Unix timestamp as string (milliseconds)
        
    Returns:
        Optional[str]: ISO datetime string or None if conversion fails
        
    Example:
        >>> timestamp = convert_unix_timestamp_to_datetime("1759605044000")
        >>> print(timestamp)
        2025-10-04T20:10:44+00:00
    """
    try:
        if not unix_timestamp:
            return None
        
        # Convert to integer (remove milliseconds if present)
        timestamp_int = int(unix_timestamp)
        
        # If timestamp is in milliseconds, convert to seconds
        if timestamp_int > 1e10:  # Greater than year 2001 in seconds
            timestamp_int = timestamp_int // 1000
        
        # Convert to datetime with UTC timezone and return ISO format
        dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
        return dt.isoformat()
        
    except (ValueError, OSError) as e:
        debug(f"Failed to convert timestamp {unix_timestamp}: {e}")
        return None


def extract_message_content(message: Dict[str, Any]) -> tuple[str, Optional[str]]:
    """
    Extract text and HTML content from a Gmail message.
    
    Args:
        message (Dict[str, Any]): Gmail message object
        
    Returns:
        tuple[str, Optional[str]]: (plain_text, html_content)
        
    Example:
        >>> text, html = extract_message_content(message)
        >>> print(f"Text: {text[:100]}...")
    """
    def extract_from_parts(parts: list) -> tuple[Optional[str], Optional[str]]:
        """Recursively extract text and HTML from message parts."""
        text_content = None
        html_content = None
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            # Extract text/plain content
            if mime_type == 'text/plain' and not text_content:
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        text_content = base64.urlsafe_b64decode(data + '==').decode('utf-8')
                    except Exception as e:
                        debug(f"Failed to decode text/plain part: {e}")
            
            # Extract text/html content
            elif mime_type == 'text/html' and not html_content:
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        html_content = base64.urlsafe_b64decode(data + '==').decode('utf-8')
                    except Exception as e:
                        debug(f"Failed to decode text/html part: {e}")
            
            # If this part has sub-parts, search recursively
            if 'parts' in part:
                sub_text, sub_html = extract_from_parts(part['parts'])
                if sub_text and not text_content:
                    text_content = sub_text
                if sub_html and not html_content:
                    html_content = sub_html
        
        return text_content, html_content
    
    # Check if message has payload
    if 'payload' not in message:
        return "No payload found in message", None
    
    payload = message['payload']
    
    # Check if payload has parts
    if 'parts' in payload:
        text_content, html_content = extract_from_parts(payload['parts'])
        return text_content or "No text content found", html_content
    
    # Check if payload itself is text content
    mime_type = payload.get('mimeType', '')
    if mime_type == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            try:
                return base64.urlsafe_b64decode(data + '==').decode('utf-8'), None
            except Exception as e:
                debug(f"Failed to decode payload text/plain: {e}")
                return f"Failed to decode text content: {e}", None
    elif mime_type == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            try:
                return "HTML content only", base64.urlsafe_b64decode(data + '==').decode('utf-8')
            except Exception as e:
                debug(f"Failed to decode payload text/html: {e}")
                return "Failed to decode HTML content", None
    
    return f"No text content found (mimeType: {mime_type})", None


def extract_attachments(message: Dict[str, Any], message_id: str, gmail_service=None) -> List[AttachmentData]:
    """
    Extract attachment information from a Gmail message and download files.
    
    Args:
        message (Dict[str, Any]): Gmail message object
        message_id (str): Gmail message ID for downloading attachments
        gmail_service: Gmail API service object (optional, will be created if needed)
        
    Returns:
        List[AttachmentData]: List of attachment metadata with downloaded file paths
        
    Example:
        >>> attachments = extract_attachments(message, "msg123", gmail_service)
        >>> print(f"Found {len(attachments)} attachments")
        >>> for att in attachments:
        ...     print(f"- {att.filename} -> {att.file_path}")
    """
    attachments = []
    
    def extract_from_parts(parts: list) -> None:
        """Recursively extract attachments from message parts."""
        for part in parts:
            # Check if this part is an attachment
            if part.get('filename'):
                attachment_id = part.get('body', {}).get('attachmentId')
                if attachment_id:
                    filename = part.get('filename')
                    mime_type = part.get('mimeType')
                    size_bytes = part.get('body', {}).get('size')
                    
                    # Create attachment data
                    attachment_data = AttachmentData(
                        attachment_id=attachment_id,
                        filename=filename,
                        mime_type=mime_type,
                        size_bytes=size_bytes
                    )
                    
                    # Download attachment if service is available
                    if gmail_service and CONFIG.gmail.download_attachments:
                        debug(f"Downloading attachment: {filename}")
                        file_path = download_attachment(gmail_service, message_id, attachment_id, filename)
                        
                        if file_path:
                            attachment_data.file_path = file_path
                            attachment_data.download_status = "downloaded"
                            info(f"Successfully downloaded: {filename} -> {file_path}")
                        else:
                            attachment_data.download_status = "failed"
                            warning(f"Failed to download attachment: {filename}")
                    else:
                        attachment_data.download_status = "pending"
                        debug(f"Attachment download skipped: {filename}")
                    
                    attachments.append(attachment_data)
                    debug(f"Found attachment: {attachment_data.filename} (ID: {attachment_data.attachment_id})")
            
            # If this part has sub-parts, search recursively
            if 'parts' in part:
                extract_from_parts(part['parts'])
    
    # Check if message has payload
    if 'payload' not in message:
        debug("No payload found in message for attachment extraction")
        return attachments
    
    payload = message['payload']
    
    # Check if payload has parts
    if 'parts' in payload:
        extract_from_parts(payload['parts'])
    
    # Check if payload itself is an attachment (single file email)
    elif payload.get('filename') and payload.get('body', {}).get('attachmentId'):
        filename = payload.get('filename')
        mime_type = payload.get('mimeType')
        size_bytes = payload.get('body', {}).get('size')
        
        attachment_data = AttachmentData(
            attachment_id=payload['body']['attachmentId'],
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes
        )
        
        # Download attachment if service is available
        if gmail_service and CONFIG.gmail.download_attachments:
            debug(f"Downloading single attachment: {filename}")
            file_path = download_attachment(gmail_service, message_id, payload['body']['attachmentId'], filename)
            
            if file_path:
                attachment_data.file_path = file_path
                attachment_data.download_status = "downloaded"
                info(f"Successfully downloaded single attachment: {filename} -> {file_path}")
            else:
                attachment_data.download_status = "failed"
                warning(f"Failed to download single attachment: {filename}")
        else:
            attachment_data.download_status = "pending"
            debug(f"Single attachment download skipped: {filename}")
        
        attachments.append(attachment_data)
        debug(f"Found single attachment: {attachment_data.filename} (ID: {attachment_data.attachment_id})")
    
    debug(f"Extracted {len(attachments)} attachments from message")
    return attachments


def create_message_data(message: Dict[str, Any], message_id: str, gmail_service=None) -> MessageData:
    """
    Create a MessageData object from a Gmail message.
    
    Args:
        message (Dict[str, Any]): Gmail message object
        message_id (str): Gmail message ID
        gmail_service: Gmail API service object (optional)
        
    Returns:
        MessageData: Structured message data
        
    Example:
        >>> msg_data = create_message_data(message, "msg123", gmail_service)
        >>> print(f"Subject: {msg_data.subject}")
    """
    headers = get_message_headers(message)
    
    # Extract content
    body_text, body_html = extract_message_content(message)
    
    # Extract attachments (with download if service provided)
    attachments = extract_attachments(message, message_id, gmail_service)
    
    # Create MessageData object
    msg_data = MessageData(
        message_id=message_id,
        thread_id=message.get('threadId', ''),
        sender=headers.get('from', 'Unknown'),
        recipient=headers.get('to', 'Unknown'),
        subject=headers.get('subject', 'No Subject'),
        date=headers.get('date', 'Unknown Date'),
        snippet=message.get('snippet', 'No snippet available'),
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
        attachment_count=len(attachments),
        internal_date=convert_unix_timestamp_to_datetime(str(message.get('internalDate', ''))),
        size_estimate=message.get('sizeEstimate'),
        label_ids=message.get('labelIds', []),
        processing_timestamp=datetime.now().isoformat()
    )
    
    return msg_data


def process_gmail_messages() -> List[MessageData]:
    """
    Process Gmail messages and return structured data.
    
    This function:
    1. Fetches all messages matching the configured search query
    2. Extracts structured data from each message
    3. Applies "Processed" label to successfully processed messages
    4. Returns a list of MessageData objects
    
    Returns:
        List[MessageData]: List of structured message data
        
    Example:
        >>> messages = process_gmail_messages()
        >>> print(f"Processed {len(messages)} messages")
        >>> for msg in messages:
        ...     print(f"- {msg.subject} from {msg.sender}")
    """
    processed_messages = []
    
    try:
        info("Starting Gmail message processing...")
        debug(f"Search query: {CONFIG.gmail.search_query}")
        debug(f"Max per run: {CONFIG.gmail.max_per_run}")
        
        # Build Gmail service
        info("Building Gmail API service...")
        service = build_gmail_service()
        debug("Gmail service built successfully")
        
        # List all messages
        info(f"Fetching all messages (up to {CONFIG.gmail.max_per_run})...")
        messages = list_messages(service, CONFIG.gmail.search_query, max_results=CONFIG.gmail.max_per_run)
        
        if not messages:
            info("No messages found matching the search query")
            info("Try adjusting CONFIG.gmail.search_query in config/dl_gmail_config.py")
            return processed_messages
        
        info(f"Found {len(messages)} messages")
        
        # Process each message in reverse order (newest last)
        for i, msg in enumerate(reversed(messages), 1):
            message_id = msg['id']
            debug(f"Processing message {i}/{len(messages)}: {message_id}")
            
            try:
                # Fetch full message details
                message = get_message(service, message_id)
                
                # Create structured data (with Gmail service for attachment downloads)
                msg_data = create_message_data(message, message_id, service)
                
                # Mark as successfully processed
                msg_data.processed_successfully = True
                
                # Apply "Processed" label and remove "INBOX" label to keep inbox clean
                label_success = apply_and_remove_labels(
                    service, 
                    message_id, 
                    add_labels=[CONFIG.gmail.processed_label],
                    remove_labels=["INBOX"]
                )
                msg_data.label_applied = label_success
                
                # Save message to database
                try:
                    db_success = save_message_to_db(msg_data)
                    msg_data.saved_to_db = db_success
                    
                    if db_success:
                        info(f"Successfully saved message to database: {msg_data.subject}")
                    else:
                        warning(f"Failed to save message to database: {msg_data.subject}")
                        
                except Exception as db_error:
                    error(f"Database error saving message {message_id}: {db_error}")
                    msg_data.saved_to_db = False
                    # Continue processing other messages even if DB save fails
                
                if label_success:
                    info(f"Successfully processed, labeled, and removed from inbox: {msg_data.subject}")
                else:
                    warning(f"Processed message but failed to update labels: {msg_data.subject}")
                
                processed_messages.append(msg_data)
                
            except Exception as e:
                error(f"Failed to process message {message_id}: {e}")
                # Continue processing other messages
                continue
        
        info(f"Gmail message processing completed - processed {len(processed_messages)} messages successfully")
        
    except FileNotFoundError as e:
        error(f"Configuration error: {e}")
        error("Please check your credentials file path in CONFIG.auth.credentials_file")
    except Exception as e:
        error(f"Unexpected error during message processing: {e}")
        raise
    
    return processed_messages


def get_processed_messages_summary(messages: List[MessageData]) -> Dict[str, Any]:
    """
    Generate a summary of processed messages.
    
    Args:
        messages (List[MessageData]): List of processed messages
        
    Returns:
        Dict[str, Any]: Summary statistics
        
    Example:
        >>> summary = get_processed_messages_summary(messages)
        >>> print(f"Total processed: {summary['total_processed']}")
    """
    total_messages = len(messages)
    successfully_labeled = sum(1 for msg in messages if msg.label_applied)
    failed_labels = total_messages - successfully_labeled
    successfully_saved_to_db = sum(1 for msg in messages if msg.saved_to_db)
    failed_db_saves = total_messages - successfully_saved_to_db
    messages_with_attachments = sum(1 for msg in messages if msg.attachment_count > 0)
    total_attachments = sum(msg.attachment_count for msg in messages)
    
    # Get unique senders
    senders = list(set(msg.sender for msg in messages))
    
    return {
        'total_messages': total_messages,
        'successfully_labeled': successfully_labeled,
        'failed_labels': failed_labels,
        'successfully_saved_to_db': successfully_saved_to_db,
        'failed_db_saves': failed_db_saves,
        'messages_with_attachments': messages_with_attachments,
        'total_attachments': total_attachments,
        'unique_senders': len(senders),
        'senders': senders,
        'processing_timestamp': datetime.now().isoformat()
    }


# Main execution function for testing
def main():
    """
    Main function for testing the dl_gmail module.
    
    This function demonstrates how to use the module and prints
    structured data for the first few messages.
    """
    try:
        # Process messages
        messages = process_gmail_messages()
        
        if not messages:
            print("No messages were processed.")
            return
        
        # Print summary
        summary = get_processed_messages_summary(messages)
        print(f"\n{'='*60}")
        print("PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Total messages processed: {summary['total_messages']}")
        print(f"Successfully labeled: {summary['successfully_labeled']}")
        print(f"Failed to label: {summary['failed_labels']}")
        print(f"Successfully saved to DB: {summary['successfully_saved_to_db']}")
        print(f"Failed DB saves: {summary['failed_db_saves']}")
        print(f"Messages with attachments: {summary['messages_with_attachments']}")
        print(f"Total attachments: {summary['total_attachments']}")
        print(f"Unique senders: {summary['unique_senders']}")
        
        # Print structured data for first 3 messages
        print(f"\n{'='*60}")
        print("MESSAGE DATA (First 3 messages)")
        print(f"{'='*60}")
        
        for i, msg in enumerate(messages[:3], 1):
            print(f"\nMESSAGE {i}:")
            print(f"  ID: {msg.message_id}")
            print(f"  Subject: {msg.subject}")
            print(f"  From: {msg.sender}")
            print(f"  Date: {msg.date}")
            print(f"  Processed: {msg.processed_successfully}")
            print(f"  Labeled: {msg.label_applied}")
            print(f"  Saved to DB: {msg.saved_to_db}")
            print(f"  Attachments: {msg.attachment_count}")
            if msg.attachments:
                for att in msg.attachments[:2]:  # Show first 2 attachments
                    print(f"    - {att.filename} ({att.mime_type})")
                if len(msg.attachments) > 2:
                    print(f"    ... and {len(msg.attachments) - 2} more")
            print(f"  Body preview: {msg.body_text[:100]}...")
            
            if i < min(3, len(messages)):
                print(f"  {'-'*40}")
        
        if len(messages) > 3:
            print(f"\n... and {len(messages) - 3} more messages")
        
    except Exception as e:
        error(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()
