"""
Gmail API Client Module

This module provides a clean interface to the Gmail API for reading emails.
It handles OAuth2 authentication, message listing, and message retrieval with
proper error handling and logging.

Key Features:
- OAuth2 authentication with token caching
- Message listing with query support
- Full message retrieval with metadata
- Error handling and logging
- PyInstaller frozen execution support

Usage:
    from .gmail_client import build_gmail_service, list_messages, get_message
    
    service = build_gmail_service()
    messages = list_messages("in:inbox", max_results=10)
    message = get_message(messages[0]['id'])
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import base64
import re
from pathlib import Path
from datetime import datetime

from dl_emails_gmail.config.dl_gmail_config import CONFIG
from common.utils.file_sys_utils import resolve_path
from .gmail_logging import logger


# Combined API scopes for both Gmail and Google Drive
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive'
]


def build_gmail_service() -> Any:
    """
    Build and return an authenticated Gmail API service.
    
    This function handles the complete OAuth2 flow:
    1. Resolves credential and token file paths using the project's path utilities
    2. Loads existing credentials from token file if available
    3. Refreshes credentials if they exist but are expired
    4. Runs the installed app flow if no valid credentials exist
    5. Saves credentials for future use
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Gmail API service
        
    Raises:
        FileNotFoundError: If credentials file is not found
        Exception: If authentication fails for any reason
        
    Example:
        >>> service = build_gmail_service()
        >>> messages = service.users().messages().list(userId='me').execute()
    """
    logger.info("Building Gmail API service...")
    
    # Resolve credential and token file paths
    credentials_path = resolve_path(CONFIG.auth.credentials_file)
    token_path = resolve_path(CONFIG.auth.token_file)
    
    logger.debug(f"Credentials file: {credentials_path}")
    logger.debug(f"Token file: {token_path}")
    
    # Check if credentials file exists
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {credentials_path}\n"
            f"Please download your OAuth2 credentials from Google Cloud Console\n"
            f"and place them at: {credentials_path}"
        )
    
    creds = None
    
    # Load existing token if available
    if token_path.exists():
        logger.debug("Loading existing token...")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            logger.debug("Token loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                creds = None
        
        if not creds:
            logger.info("Running OAuth2 flow...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("OAuth2 flow completed successfully")
            except Exception as e:
                raise Exception(f"OAuth2 authentication failed: {e}")
        
        # Save the credentials for the next run
        logger.debug(f"Saving credentials to: {token_path}")
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        logger.debug("Credentials saved successfully")
    
    # Build the Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service built successfully")
        return service
    except Exception as e:
        raise Exception(f"Failed to build Gmail service: {e}")


def list_messages(service: Any, query: str, max_results: int = 1) -> List[Dict[str, Any]]:
    """
    List messages matching the given query.
    
    Args:
        service: Authenticated Gmail API service
        query (str): Gmail search query (e.g., "in:inbox", "from:example@gmail.com")
        max_results (int): Maximum number of messages to return (default: 1)
        
    Returns:
        List[Dict[str, Any]]: List of message metadata dictionaries
        
    Raises:
        HttpError: If the Gmail API request fails
        Exception: If there's an unexpected error
        
    Example:
        >>> service = build_gmail_service()
        >>> messages = list_messages(service, "in:inbox", max_results=10)
        >>> print(f"Found {len(messages)} messages")
    """
    logger.info(f"Listing messages with query: '{query}' (max: {max_results})")
    
    try:
        # Call the Gmail API
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} messages")
        
        if not messages:
            logger.warning("No messages found matching the query")
        
        return messages
        
    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing messages: {e}")
        raise


def get_message(service: Any, message_id: str, format: str = "full") -> Dict[str, Any]:
    """
    Get a specific message by ID.
    
    Args:
        service: Authenticated Gmail API service
        message_id (str): The ID of the message to retrieve
        format (str): Message format - 'full', 'metadata', 'minimal', 'raw' (default: 'full')
        
    Returns:
        Dict[str, Any]: Complete message data including headers, body, etc.
        
    Raises:
        HttpError: If the Gmail API request fails
        Exception: If there's an unexpected error
        
    Example:
        >>> service = build_gmail_service()
        >>> message = get_message(service, "message_id_123")
        >>> print(f"Subject: {message['payload']['headers'][0]['value']}")
    """
    logger.info(f"Retrieving message {message_id} (format: {format})")
    
    try:
        # Call the Gmail API
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format=format
        ).execute()
        
        logger.debug(f"Message retrieved successfully: {message_id}")
        return message
        
    except HttpError as error:
        logger.error(f"Gmail API error retrieving message {message_id}: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving message {message_id}: {e}")
        raise


def get_message_headers(message: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract headers from a Gmail message in a convenient dictionary format.
    
    Args:
        message (Dict[str, Any]): Gmail message object
        
    Returns:
        Dict[str, str]: Dictionary mapping header names to values
        
    Example:
        >>> headers = get_message_headers(message)
        >>> print(f"From: {headers.get('From', 'Unknown')}")
        >>> print(f"Subject: {headers.get('Subject', 'No Subject')}")
    """
    headers = {}
    
    if 'payload' in message and 'headers' in message['payload']:
        for header in message['payload']['headers']:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            headers[name] = value
    
    return headers


def apply_label_to_message(service: Any, message_id: str, label_name: str) -> bool:
    """
    Apply a label to a Gmail message.
    
    Args:
        service: Authenticated Gmail API service
        message_id (str): Gmail message ID
        label_name (str): Name of the label to apply
        
    Returns:
        bool: True if label was applied successfully, False otherwise
        
    Example:
        >>> success = apply_label_to_message(service, "msg123", "Processed")
        >>> if success:
        ...     print("Label applied successfully")
    """
    try:
        # First, get or create the label
        label_id = get_or_create_label(service, label_name)
        if not label_id:
            logger.error(f"Failed to get or create label: {label_name}")
            return False
        
        # Apply the label to the message
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        logger.debug(f"Successfully applied label '{label_name}' to message {message_id}")
        return True
        
    except HttpError as e:
        logger.error(f"HTTP error applying label to message {message_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error applying label to message {message_id}: {e}")
        return False


def remove_label_from_message(service: Any, message_id: str, label_name: str) -> bool:
    """
    Remove a label from a Gmail message.
    
    Args:
        service: Authenticated Gmail API service
        message_id (str): Gmail message ID
        label_name (str): Name of the label to remove
        
    Returns:
        bool: True if label was removed successfully, False otherwise
        
    Example:
        >>> success = remove_label_from_message(service, "msg123", "INBOX")
        >>> if success:
        ...     print("Label removed successfully")
    """
    try:
        # Get the label ID
        label_id = get_label_id(service, label_name)
        if not label_id:
            logger.warning(f"Label '{label_name}' not found - cannot remove from message {message_id}")
            return False
        
        # Remove the label from the message
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': [label_id]}
        ).execute()
        
        logger.debug(f"Successfully removed label '{label_name}' from message {message_id}")
        return True
        
    except HttpError as e:
        logger.error(f"HTTP error removing label from message {message_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error removing label from message {message_id}: {e}")
        return False


def apply_and_remove_labels(service: Any, message_id: str, add_labels: List[str], remove_labels: List[str]) -> bool:
    """
    Apply and remove multiple labels from a Gmail message in a single operation.
    
    Args:
        service: Authenticated Gmail API service
        message_id (str): Gmail message ID
        add_labels (List[str]): List of label names to add
        remove_labels (List[str]): List of label names to remove
        
    Returns:
        bool: True if all operations were successful, False otherwise
        
    Example:
        >>> success = apply_and_remove_labels(service, "msg123", ["Processed"], ["INBOX"])
        >>> if success:
        ...     print("Labels updated successfully")
    """
    try:
        add_label_ids = []
        remove_label_ids = []
        
        # Get label IDs for labels to add
        for label_name in add_labels:
            label_id = get_or_create_label(service, label_name)
            if label_id:
                add_label_ids.append(label_id)
            else:
                logger.error(f"Failed to get/create label for adding: {label_name}")
        
        # Get label IDs for labels to remove
        for label_name in remove_labels:
            label_id = get_label_id(service, label_name)
            if label_id:
                remove_label_ids.append(label_id)
            else:
                logger.warning(f"Label not found for removal: {label_name}")
        
        # Prepare the modify request body
        modify_body = {}
        if add_label_ids:
            modify_body['addLabelIds'] = add_label_ids
        if remove_label_ids:
            modify_body['removeLabelIds'] = remove_label_ids
        
        # Skip if no changes to make
        if not modify_body:
            logger.debug(f"No label changes to make for message {message_id}")
            return True
        
        # Apply the changes
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body=modify_body
        ).execute()
        
        logger.debug(f"Successfully updated labels for message {message_id}: add={add_labels}, remove={remove_labels}")
        return True
        
    except HttpError as e:
        logger.error(f"HTTP error updating labels for message {message_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating labels for message {message_id}: {e}")
        return False


def get_label_id(service: Any, label_name: str) -> Optional[str]:
    """
    Get the ID of an existing label by name.
    
    Args:
        service: Authenticated Gmail API service
        label_name (str): Name of the label
        
    Returns:
        Optional[str]: Label ID if found, None otherwise
        
    Example:
        >>> label_id = get_label_id(service, "INBOX")
        >>> if label_id:
        ...     print(f"INBOX label ID: {label_id}")
    """
    try:
        labels_result = service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        return None
        
    except HttpError as e:
        logger.error(f"HTTP error getting label ID for '{label_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting label ID for '{label_name}': {e}")
        return None


def get_or_create_label(service: Any, label_name: str) -> Optional[str]:
    """
    Get existing label ID or create a new label if it doesn't exist.
    
    Args:
        service: Authenticated Gmail API service
        label_name (str): Name of the label
        
    Returns:
        Optional[str]: Label ID if successful, None otherwise
        
    Example:
        >>> label_id = get_or_create_label(service, "Processed")
        >>> if label_id:
        ...     print(f"Label ID: {label_id}")
    """
    try:
        # First, try to find existing label
        labels_result = service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        for label in labels:
            if label['name'] == label_name:
                logger.debug(f"Found existing label '{label_name}' with ID: {label['id']}")
                return label['id']
        
        # Label doesn't exist, create it
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        created_label = service.users().labels().create(
            userId='me',
            body=label_object
        ).execute()
        
        logger.info(f"Created new label '{label_name}' with ID: {created_label['id']}")
        return created_label['id']
        
    except HttpError as e:
        logger.error(f"HTTP error getting/creating label '{label_name}': {e}")
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem storage.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename safe for filesystem
        
    Example:
        >>> sanitize_filename("document with spaces/file.pdf")
        "document_with_spaces_file.pdf"
    """
    if not filename:
        return "unnamed_attachment"
    
    # Remove or replace invalid characters
    # Windows: < > : " | ? * \
    # Unix: / (and null bytes)
    invalid_chars = r'[<>:"|?*\\\/\x00]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty after sanitization
    if not sanitized:
        return "unnamed_attachment"
    
    # Limit filename length (Windows has 255 char limit for full path)
    if len(sanitized) > 200:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:200-len(ext)] + ext
    
    return sanitized


def create_unique_filepath(download_dir: Path, filename: str) -> Path:
    """
    Create a unique filepath handling duplicates.
    
    Args:
        download_dir (Path): Base download directory
        filename (str): Original filename
        
    Returns:
        Path: Unique filepath
        
    Example:
        >>> create_unique_filepath(Path("/downloads"), "document.pdf")
        Path("/downloads/document.pdf")
        >>> # If document.pdf exists, returns Path("/downloads/document_1.pdf")
    """
    if not CONFIG.gmail.handle_duplicate_filenames:
        return download_dir / filename
    
    base_path = download_dir / filename
    
    if not base_path.exists():
        return base_path
    
    # Handle duplicates by adding counter
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_path = download_dir / new_filename
        
        if not new_path.exists():
            return new_path
        
        counter += 1
        
        # Safety check to prevent infinite loop
        if counter > 1000:
            logger.warning(f"Too many duplicates for {filename}, using timestamp")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{name}_{timestamp}{ext}"
            return download_dir / new_filename


def download_attachment(service, message_id: str, attachment_id: str, filename: str) -> Optional[str]:
    """
    Download an attachment from Gmail and save it to disk.
    
    Args:
        service: Gmail API service object
        message_id (str): Gmail message ID
        attachment_id (str): Gmail attachment ID
        filename (str): Original filename
        
    Returns:
        Optional[str]: File path if successful, None if failed
        
    Example:
        >>> file_path = download_attachment(service, "msg123", "att456", "document.pdf")
        >>> print(f"Downloaded to: {file_path}")
    """
    try:
        if not CONFIG.gmail.download_attachments:
            logger.debug(f"Attachment download disabled, skipping: {filename}")
            return None
        
        # Get attachment data from Gmail API
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        # Decode attachment data
        file_data = base64.urlsafe_b64decode(attachment['data'])
        file_size = len(file_data)
        
        # Check file size limit
        if file_size > CONFIG.gmail.max_attachment_size:
            logger.warning(f"Attachment {filename} too large ({file_size} bytes), skipping")
            return None
        
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        download_dir = Path(CONFIG.gmail.attachment_download_dir) / date_str
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename and create unique path
        safe_filename = sanitize_filename(filename)
        file_path = create_unique_filepath(download_dir, safe_filename)
        
        # Write file to disk
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Downloaded attachment: {filename} -> {file_path} ({file_size} bytes)")
        return str(file_path)
        
    except HttpError as e:
        logger.error(f"HTTP error downloading attachment {filename}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading attachment {filename}: {e}")
        return None
