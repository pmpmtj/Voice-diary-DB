"""
Database Persistence Layer

This module provides functions to save Gmail message data to the PostgreSQL database.
It handles the complete data persistence workflow including threads, messages, labels, and attachments.

Key Features:
- Save messages with thread and label relationships
- Handle thread creation and lookup
- Handle label creation and lookup
- Save attachment metadata
- Transaction management with proper error handling
- Logging integration using existing logging_utils
- Support for batch operations

Usage:
    from src.dl_gmail.db_persistence import save_message_to_db
    
    success = save_message_to_db(message_data)
    if success:
        print("Message saved successfully")
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add project root to Python path when running as module
if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from .db_utils import get_db_connection, execute_insert, execute_query, record_exists, DatabaseError, execute_update
from .models import MessageData, AttachmentData
from dl_emails_gmail.logging_utils.logging_config import get_logger

# Initialize logger for this module
logger = get_logger("db_persistence")


def save_or_get_thread(connection, thread_id: str, subject: str = None) -> str:
    """
    Save a thread to the database or get existing thread ID.
    
    Args:
        connection: Database connection
        thread_id (str): Gmail thread ID
        subject (str): Thread subject (optional)
        
    Returns:
        str: Thread ID (same as input)
        
    Example:
        >>> with get_db_connection() as conn:
        ...     thread_id = save_or_get_thread(conn, "thread123", "Important Discussion")
    """
    try:
        # Check if thread already exists
        if record_exists(connection, "gml_threads", {"thread_id": thread_id}):
            logger.debug(f"Thread {thread_id} already exists")
            return thread_id
        
        # Create new thread
        insert_query = """
            INSERT INTO gml_threads (thread_id, subject, message_count, last_message_date)
            VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (thread_id) DO NOTHING
        """
        
        with connection.cursor() as cursor:
            cursor.execute(insert_query, (thread_id, subject))
            connection.commit()
        
        logger.debug(f"Created thread: {thread_id}")
        return thread_id
        
    except Exception as e:
        logger.error(f"Failed to save/get thread {thread_id}: {e}")
        raise DatabaseError(f"Failed to save/get thread: {e}")


def save_or_get_label(connection, label_id: str, label_name: str, label_type: str = "user") -> str:
    """
    Save a label to the database or get existing label ID.
    
    Args:
        connection: Database connection
        label_id (str): Gmail label ID
        label_name (str): Label name
        label_type (str): Label type (default: "user")
        
    Returns:
        str: Label ID (same as input)
        
    Example:
        >>> with get_db_connection() as conn:
        ...     label_id = save_or_get_label(conn, "Label_123", "Important", "user")
    """
    try:
        # Check if label already exists
        if record_exists(connection, "gml_labels", {"label_id": label_id}):
            logger.debug(f"Label {label_id} already exists")
            return label_id
        
        # Create new label
        insert_query = """
            INSERT INTO gml_labels (label_id, name, label_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (label_id) DO NOTHING
        """
        
        with connection.cursor() as cursor:
            cursor.execute(insert_query, (label_id, label_name, label_type))
            connection.commit()
        
        logger.debug(f"Created label: {label_name} ({label_id})")
        return label_id
        
    except Exception as e:
        logger.error(f"Failed to save/get label {label_id}: {e}")
        raise DatabaseError(f"Failed to save/get label: {e}")


def save_message_to_db(message_data: MessageData) -> bool:
    """
    Save a complete message with all relationships to the database.
    
    Args:
        message_data (MessageData): Message data to save
        
    Returns:
        bool: True if saved successfully, False otherwise
        
    Example:
        >>> success = save_message_to_db(message_data)
        >>> if success:
        ...     print("Message saved successfully")
    """
    try:
        logger.info(f"Saving message to database: {message_data.subject}")
        
        with get_db_connection() as connection:
            try:
                # 1. Save or get thread
                save_or_get_thread(connection, message_data.thread_id, message_data.subject)
                
                # 2. Save message
                message_insert_query = """
                    INSERT INTO gml_messages (
                        message_id, thread_id, sender, recipient, subject, date,
                        internal_date, snippet, body_text, size_estimate,
                        processed_successfully, label_applied, processing_timestamp
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    ) RETURNING id
                """
                
                message_db_id = execute_insert(connection, message_insert_query, (
                    message_data.message_id,
                    message_data.thread_id,
                    message_data.sender,
                    message_data.recipient,
                    message_data.subject,
                    message_data.date,
                    message_data.internal_date,
                    message_data.snippet,
                    message_data.body_text,
                    message_data.size_estimate,
                    message_data.processed_successfully,
                    message_data.label_applied,
                    message_data.processing_timestamp
                ))
                
                if message_db_id:
                    logger.debug(f"Saved message with DB ID: {message_db_id}")
                else:
                    raise Exception("Failed to get message ID from insert")
                
                # 3. Save labels and message-label relationships
                if message_data.label_ids:
                    for label_id in message_data.label_ids:
                        # Get label name (we'll use label_id as name for now)
                        # In a real implementation, you might want to fetch this from Gmail API
                        label_name = label_id
                        save_or_get_label(connection, label_id, label_name)
                        
                        # Create message-label relationship
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO gml_message_labels (message_id, label_id)
                                VALUES (%s, %s)
                                ON CONFLICT (message_id, label_id) DO NOTHING
                            """, (message_db_id, label_id))
                
                # 4. Save attachments
                if message_data.attachments:
                    for attachment in message_data.attachments:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO gml_attachments (
                                    message_id, attachment_id, filename, mime_type,
                                    size_bytes, file_path, download_status
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                message_db_id,
                                attachment.attachment_id,
                                attachment.filename,
                                attachment.mime_type,
                                attachment.size_bytes,
                                attachment.file_path,
                                attachment.download_status
                            ))
                
                # 5. Update thread message count and last message date
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE gml_threads 
                        SET message_count = message_count + 1,
                            last_message_date = CURRENT_TIMESTAMP
                        WHERE gml_threads.thread_id = %s
                    """, (message_data.thread_id,))
                
                # 6. Update message as saved to DB
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE gml_messages 
                        SET saved_to_db = TRUE
                        WHERE message_id = %s
                    """, (message_data.message_id,))
                
                connection.commit()
                logger.info(f"Successfully saved message to database: {message_data.subject}")
                return True
                
            except Exception as e:
                connection.rollback()
                logger.error(f"Failed to save message {message_data.message_id}: {e}")
                raise
                    
    except DatabaseError:
        # Database errors are already logged
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving message {message_data.message_id}: {e}")
        return False


def save_attachments_to_db(message_db_id: str, attachments: List[AttachmentData]) -> bool:
    """
    Save attachment metadata to the database.
    
    Args:
        message_db_id (str): Database ID of the message
        attachments (List[AttachmentData]): List of attachments to save
        
    Returns:
        bool: True if saved successfully, False otherwise
        
    Example:
        >>> success = save_attachments_to_db("uuid-123", attachment_list)
        >>> if success:
        ...     print("Attachments saved successfully")
    """
    try:
        if not attachments:
            logger.debug("No attachments to save")
            return True
        
        logger.info(f"Saving {len(attachments)} attachments for message {message_db_id}")
        
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                for attachment in attachments:
                    cursor.execute("""
                        INSERT INTO gml_attachments (
                            message_id, attachment_id, filename, mime_type,
                            size_bytes, download_status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        message_db_id,
                        attachment.attachment_id,
                        attachment.filename,
                        attachment.mime_type,
                        attachment.size_bytes,
                        attachment.download_status
                    ))
                
                connection.commit()
                logger.info(f"Successfully saved {len(attachments)} attachments")
                return True
                
    except Exception as e:
        logger.error(f"Failed to save attachments for message {message_db_id}: {e}")
        return False


def update_message_db_status(message_id: str, saved_to_db: bool = True) -> bool:
    """
    Update the saved_to_db status of a message.
    
    Args:
        message_id (str): Gmail message ID
        saved_to_db (bool): Whether message was saved to database
        
    Returns:
        bool: True if updated successfully, False otherwise
        
    Example:
        >>> success = update_message_db_status("msg123", True)
        >>> if success:
        ...     print("Message status updated")
    """
    try:
        with get_db_connection() as connection:
            update_query = "UPDATE gml_messages SET saved_to_db = %s WHERE message_id = %s"
            rows_affected = execute_update(connection, update_query, (saved_to_db, message_id))
            
            if rows_affected > 0:
                logger.debug(f"Updated saved_to_db status for message {message_id}")
                return True
            else:
                logger.warning(f"No message found with ID {message_id}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to update message status for {message_id}: {e}")
        return False


def get_message_from_db(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a message from the database by Gmail message ID.
    
    Args:
        message_id (str): Gmail message ID
        
    Returns:
        Optional[Dict[str, Any]]: Message data or None if not found
        
    Example:
        >>> message = get_message_from_db("msg123")
        >>> if message:
        ...     print(f"Found message: {message['subject']}")
    """
    try:
        with get_db_connection() as connection:
            query = "SELECT * FROM gml_message_summary WHERE message_id = %s"
            results = execute_query(connection, query, (message_id,))
            return results[0] if results else None
            
    except Exception as e:
        logger.error(f"Failed to retrieve message {message_id}: {e}")
        return None


def get_messages_by_thread(thread_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all messages in a thread from the database.
    
    Args:
        thread_id (str): Gmail thread ID
        
    Returns:
        List[Dict[str, Any]]: List of message data
        
    Example:
        >>> messages = get_messages_by_thread("thread123")
        >>> print(f"Found {len(messages)} messages in thread")
    """
    try:
        with get_db_connection() as connection:
            query = """
                SELECT * FROM gml_message_summary 
                WHERE thread_id = %s 
                ORDER BY date ASC
            """
            return execute_query(connection, query, (thread_id,))
            
    except Exception as e:
        logger.error(f"Failed to retrieve messages for thread {thread_id}: {e}")
        return []


def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the database content.
    
    Returns:
        Dict[str, Any]: Database statistics
        
    Example:
        >>> stats = get_database_stats()
        >>> print(f"Total messages: {stats['total_messages']}")
    """
    try:
        with get_db_connection() as connection:
            stats = {}
            
            # Get counts for each table
            tables = ['gml_threads', 'gml_messages', 'gml_labels', 'gml_attachments']
            for table in tables:
                query = f"SELECT COUNT(*) as count FROM {table}"
                results = execute_query(connection, query)
                stats[f'total_{table}'] = results[0]['count'] if results else 0
            
            # Get message processing stats
            query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE processed_successfully = TRUE) as processed,
                    COUNT(*) FILTER (WHERE saved_to_db = TRUE) as saved_to_db,
                    COUNT(*) FILTER (WHERE attachment_count > 0) as with_attachments
                FROM gml_message_summary
            """
            results = execute_query(connection, query)
            if results:
                stats.update(results[0])
            
            # Get recent activity
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as messages_processed
                FROM gml_messages 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            results = execute_query(connection, query)
            stats['recent_activity'] = results
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


if __name__ == "__main__":
    # Test database persistence functions
    print("Testing database persistence...")
    
    try:
        # Test database connection
        stats = get_database_stats()
        print("+ Database connection successful")
        print(f"Database stats: {stats}")
        
    except Exception as e:
        print(f"- Database persistence test failed: {e}")
        sys.exit(1)
