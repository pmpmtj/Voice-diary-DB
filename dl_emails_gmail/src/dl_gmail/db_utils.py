"""
Database Utilities Module

This module provides database connection management and utility functions for the Gmail downloader.
It handles PostgreSQL connections, transaction management, and common database operations.

Key Features:
- Connection pooling with psycopg2
- Transaction management with proper error handling
- CRUD operations for all tables
- Logging integration using existing logging_utils
- Automatic connection cleanup
- Support for both individual operations and batch operations

Usage:
    from src.dl_gmail.db_utils import get_db_connection, execute_query
    
    with get_db_connection() as conn:
        result = execute_query(conn, "SELECT * FROM gml_messages LIMIT 10")
"""

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple
import sys
from pathlib import Path

# Add project root to Python path when running as module
if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from dl_emails_gmail.config.db_config import DB_CONFIG
from dl_emails_gmail.logging_utils.logging_config import get_logger

# Initialize logger for this module
logger = get_logger("db_utils")


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


@contextmanager
def get_db_connection(autocommit: bool = False):
    """
    Context manager for database connections.
    
    Args:
        autocommit (bool): Whether to enable autocommit mode
        
    Yields:
        psycopg2.connection: Database connection
        
    Raises:
        DatabaseError: If connection fails
        
    Example:
        >>> with get_db_connection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT COUNT(*) FROM gml_messages")
        ...     count = cursor.fetchone()[0]
    """
    connection = None
    try:
        # Validate configuration
        is_valid, error = DB_CONFIG.validate_config()
        if not is_valid:
            raise DatabaseError(f"Database configuration error: {error}")
        
        logger.debug(f"Connecting to database: {DB_CONFIG.host}:{DB_CONFIG.port}/{DB_CONFIG.database}")
        
        # Create connection
        connection = psycopg2.connect(
            **DB_CONFIG.get_connection_params(),
            cursor_factory=RealDictCursor
        )
        
        # Set isolation level if autocommit is requested
        if autocommit:
            connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        logger.debug("Database connection established")
        yield connection
        
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise DatabaseError(f"Failed to connect to database: {e}")
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise DatabaseError(f"Unexpected database error: {e}")
    finally:
        if connection:
            try:
                connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")


def execute_query(connection, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries.
    
    Args:
        connection: Database connection
        query (str): SQL query to execute
        params (Optional[Tuple]): Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results as list of dictionaries
        
    Raises:
        DatabaseError: If query execution fails
        
    Example:
        >>> with get_db_connection() as conn:
        ...     results = execute_query(conn, "SELECT * FROM gml_messages WHERE sender = %s", ("test@example.com",))
        ...     for row in results:
        ...         print(f"Subject: {row['subject']}")
    """
    try:
        with connection.cursor() as cursor:
            logger.debug(f"Executing query: {query[:100]}...")
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert RealDictRow objects to regular dictionaries
            return [dict(row) for row in results]
            
    except psycopg2.Error as e:
        logger.error(f"Query execution failed: {e}")
        logger.error(f"Query: {query}")
        if params:
            logger.error(f"Params: {params}")
        raise DatabaseError(f"Query execution failed: {e}")


def execute_insert(connection, query: str, params: Optional[Tuple] = None) -> Optional[str]:
    """
    Execute an INSERT query and return the inserted ID.
    
    Args:
        connection: Database connection
        query (str): INSERT SQL query
        params (Optional[Tuple]): Query parameters
        
    Returns:
        Optional[str]: Inserted record ID if available
        
    Example:
        >>> with get_db_connection() as conn:
        ...     message_id = execute_insert(conn, 
        ...         "INSERT INTO gml_messages (message_id, thread_id, sender) VALUES (%s, %s, %s) RETURNING id",
        ...         ("msg123", "thread456", "test@example.com"))
        ...     print(f"Inserted message ID: {message_id}")
    """
    try:
        with connection.cursor() as cursor:
            logger.debug(f"Executing insert: {query[:100]}...")
            cursor.execute(query, params)
            
            # Try to get the returned ID if RETURNING clause is present
            if 'RETURNING' in query.upper():
                try:
                    result = cursor.fetchone()
                    if result:
                        # Handle both dict and tuple results
                        if isinstance(result, dict):
                            return str(result['id'])
                        else:
                            return str(result[0])
                except Exception as e:
                    logger.debug(f"No result from RETURNING clause: {e}")
            
            connection.commit()
            logger.debug("Insert completed successfully")
            return None
            
    except psycopg2.Error as e:
        logger.error(f"Insert execution failed: {e}")
        logger.error(f"Query: {query}")
        if params:
            logger.error(f"Params: {params}")
        connection.rollback()
        raise DatabaseError(f"Insert execution failed: {e}")


def execute_update(connection, query: str, params: Optional[Tuple] = None) -> int:
    """
    Execute an UPDATE query and return the number of affected rows.
    
    Args:
        connection: Database connection
        query (str): UPDATE SQL query
        params (Optional[Tuple]): Query parameters
        
    Returns:
        int: Number of affected rows
        
    Example:
        >>> with get_db_connection() as conn:
        ...     rows_updated = execute_update(conn,
        ...         "UPDATE gml_messages SET saved_to_db = %s WHERE message_id = %s",
        ...         (True, "msg123"))
        ...     print(f"Updated {rows_updated} rows")
    """
    try:
        with connection.cursor() as cursor:
            logger.debug(f"Executing update: {query[:100]}...")
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
            
            connection.commit()
            logger.debug(f"Update completed, {rows_affected} rows affected")
            return rows_affected
            
    except psycopg2.Error as e:
        logger.error(f"Update execution failed: {e}")
        logger.error(f"Query: {query}")
        if params:
            logger.error(f"Params: {params}")
        connection.rollback()
        raise DatabaseError(f"Update execution failed: {e}")


def execute_batch_insert(connection, table: str, columns: List[str], values: List[Tuple]) -> int:
    """
    Execute a batch INSERT operation for better performance.
    
    Args:
        connection: Database connection
        table (str): Table name
        columns (List[str]): Column names
        values (List[Tuple]): List of value tuples
        
    Returns:
        int: Number of inserted rows
        
    Example:
        >>> with get_db_connection() as conn:
        ...     values = [("label1", "Label 1"), ("label2", "Label 2")]
        ...     count = execute_batch_insert(conn, "gml_labels", ["label_id", "name"], values)
        ...     print(f"Inserted {count} labels")
    """
    try:
        if not values:
            logger.warning("No values provided for batch insert")
            return 0
        
        columns_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({columns_str}) VALUES {placeholders}"
        
        logger.debug(f"Executing batch insert into {table}: {len(values)} rows")
        
        with connection.cursor() as cursor:
            execute_values(cursor, query, values, template=None, page_size=1000)
            rows_inserted = cursor.rowcount
            
            connection.commit()
            logger.debug(f"Batch insert completed, {rows_inserted} rows inserted")
            return rows_inserted
            
    except psycopg2.Error as e:
        logger.error(f"Batch insert failed: {e}")
        logger.error(f"Table: {table}, Columns: {columns}")
        connection.rollback()
        raise DatabaseError(f"Batch insert failed: {e}")


def get_record_by_id(connection, table: str, record_id: str, id_column: str = "id") -> Optional[Dict[str, Any]]:
    """
    Get a single record by its ID.
    
    Args:
        connection: Database connection
        table (str): Table name
        record_id (str): Record ID
        id_column (str): ID column name (default: "id")
        
    Returns:
        Optional[Dict[str, Any]]: Record data or None if not found
        
    Example:
        >>> with get_db_connection() as conn:
        ...     message = get_record_by_id(conn, "gml_messages", "msg123", "message_id")
        ...     if message:
        ...         print(f"Found message: {message['subject']}")
    """
    try:
        query = f"SELECT * FROM {table} WHERE {id_column} = %s"
        results = execute_query(connection, query, (record_id,))
        return results[0] if results else None
        
    except Exception as e:
        logger.error(f"Failed to get record from {table}: {e}")
        raise DatabaseError(f"Failed to get record: {e}")


def record_exists(connection, table: str, conditions: Dict[str, Any]) -> bool:
    """
    Check if a record exists based on given conditions.
    
    Args:
        connection: Database connection
        table (str): Table name
        conditions (Dict[str, Any]): Conditions to check
        
    Returns:
        bool: True if record exists, False otherwise
        
    Example:
        >>> with get_db_connection() as conn:
        ...     exists = record_exists(conn, "gml_messages", {"message_id": "msg123"})
        ...     print(f"Message exists: {exists}")
    """
    try:
        if not conditions:
            return False
        
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1"
        params = tuple(conditions.values())
        
        results = execute_query(connection, query, params)
        return len(results) > 0
        
    except Exception as e:
        logger.error(f"Failed to check record existence in {table}: {e}")
        raise DatabaseError(f"Failed to check record existence: {e}")


def get_table_count(connection, table: str) -> int:
    """
    Get the total number of records in a table.
    
    Args:
        connection: Database connection
        table (str): Table name
        
    Returns:
        int: Number of records
        
    Example:
        >>> with get_db_connection() as conn:
        ...     count = get_table_count(conn, "gml_messages")
        ...     print(f"Total messages: {count}")
    """
    try:
        results = execute_query(connection, f"SELECT COUNT(*) as count FROM {table}")
        return results[0]['count'] if results else 0
        
    except Exception as e:
        logger.error(f"Failed to get count for table {table}: {e}")
        raise DatabaseError(f"Failed to get table count: {e}")


def test_database_connection() -> bool:
    """
    Test database connection and return status.
    
    Returns:
        bool: True if connection successful, False otherwise
        
    Example:
        >>> if test_database_connection():
        ...     print("Database connection successful")
    """
    try:
        with get_db_connection() as conn:
            results = execute_query(conn, "SELECT 1 as test")
            return len(results) > 0 and results[0]['test'] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test database connection and basic operations
    print("Testing database connection...")
    
    if test_database_connection():
        print("+ Database connection successful")
        
        try:
            with get_db_connection() as conn:
                # Test basic operations
                message_count = get_table_count(conn, "gml_messages")
                thread_count = get_table_count(conn, "gml_threads")
                label_count = get_table_count(conn, "gml_labels")
                
                print(f"+ Messages in database: {message_count}")
                print(f"+ Threads in database: {thread_count}")
                print(f"+ Labels in database: {label_count}")
                
        except Exception as e:
            print(f"- Database operations failed: {e}")
    else:
        print("- Database connection failed")
        sys.exit(1)
