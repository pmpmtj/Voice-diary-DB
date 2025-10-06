"""
Database Utilities Module

This module provides database connection and utility functions for the transcription
logging application. It handles PostgreSQL connections, transaction management,
and provides helper functions for database operations.

Key Features:
- PostgreSQL connection management with connection pooling
- Transaction management with automatic rollback on errors
- Database initialization and table creation
- Utility functions for common database operations
- Comprehensive error handling and logging

The utilities handle:
- Database connection establishment and cleanup
- Transaction management with context managers
- SQL script execution for table creation
- Connection pooling for better performance
- Error handling with detailed logging

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import json
import uuid
import logging
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pathlib import Path

from common.logging_utils.logging_config import get_logger

# Import config using proper module path
from txt_audio_to_db.config.db_config import DB_CONFIG


class DatabaseManager:
    """
    Database manager for handling PostgreSQL connections and operations.
    
    This class provides a centralized way to manage database connections,
    execute queries, and handle transactions. It supports connection pooling
    and automatic cleanup.
    """
    
    def __init__(self):
        """Initialize the database manager with configuration."""
        self.logger = get_logger("db_manager")
        self.db_config = DB_CONFIG
        self._connection_pool = None
        
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Get database connection parameters from configuration.
        
        Returns:
            Dict[str, Any]: Connection parameters for psycopg2
        """
        return {
            'host': self.db_config.host,
            'port': self.db_config.port,
            'database': self.db_config.database,
            'user': self.db_config.user,
            'password': self.db_config.password,
            'cursor_factory': psycopg2.extras.RealDictCursor
        }
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection with automatic cleanup.
        
        This context manager ensures proper connection handling with
        automatic cleanup and error handling.
        
        Yields:
            psycopg2.connection: Database connection
            
        Raises:
            psycopg2.Error: Database connection or query errors
        """
        connection = None
        try:
            self.logger.debug("Establishing database connection")
            connection = psycopg2.connect(**self.get_connection_params())
            connection.autocommit = False
            self.logger.debug("Database connection established successfully")
            yield connection
        except psycopg2.Error as e:
            self.logger.error(f"Database error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                self.logger.debug("Closing database connection")
                connection.close()
    
    @contextmanager
    def transaction(self):
        """
        Execute database operations within a transaction.
        
        This context manager provides transaction management with automatic
        commit on success and rollback on error.
        
        Yields:
            psycopg2.connection: Database connection within transaction
        """
        with self.get_connection() as conn:
            try:
                self.logger.debug("Starting database transaction")
                yield conn
                conn.commit()
                self.logger.debug("Database transaction committed successfully")
            except Exception as e:
                self.logger.error(f"Database transaction failed, rolling back: {e}")
                conn.rollback()
                raise
    
    def execute_sql_script(self, script_path: Union[str, Path]) -> None:
        """
        Execute a SQL script file.
        
        Args:
            script_path (Union[str, Path]): Path to the SQL script file
            
        Raises:
            FileNotFoundError: If the script file doesn't exist
            psycopg2.Error: If there's a database error during execution
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"SQL script not found: {script_path}")
        
        self.logger.info(f"Executing SQL script: {script_path}")
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(script_path.read_text(encoding='utf-8'))
                conn.commit()
        
        self.logger.info("SQL script executed successfully")
    
    def initialize_database(self, schema_script_path: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the database by creating tables.
        
        Args:
            schema_script_path (Optional[Union[str, Path]]): Path to schema script.
                                                           Defaults to database/gdrive_schema.sql
        """
        if schema_script_path is None:
            # Get the project root and look for database/gdrive_schema.sql
            script_dir = Path(__file__).resolve().parent.parent.parent.parent
            schema_script_path = script_dir / "database" / "gdrive_schema.sql"
        
        self.logger.info("Initializing database with schema")
        self.execute_sql_script(schema_script_path)
        self.logger.info("Database initialization completed")


class TranscriptionIngestion:
    """
    Handles ingestion of transcription data into the normalized database schema.
    
    This class provides methods to parse transcription JSON responses and insert
    them into the appropriate database tables with proper relationships.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the transcription ingestion handler.
        
        Args:
            db_manager (Optional[DatabaseManager]): Database manager instance.
                                                   Creates new one if None.
        """
        self.logger = get_logger("transcription_ingestion")
        self.db_manager = db_manager or DatabaseManager()
    
    def parse_transcription_response(self, response_data: Union[str, Dict]) -> Dict[str, Any]:
        """
        Parse transcription response JSON into structured data.
        
        Args:
            response_data (Union[str, Dict]): JSON string or dict containing response
            
        Returns:
            Dict[str, Any]: Parsed transcription data
            
        Raises:
            ValueError: If response data is invalid
            json.JSONDecodeError: If JSON parsing fails
        """
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                raise
        
        if not isinstance(response_data, dict):
            raise ValueError("Response data must be a dictionary")
        
        # Extract main transcription text
        text = response_data.get('text', '')
        if not text or not text.strip():
            raise ValueError("Transcription text is empty or missing")
        
        # Extract metadata
        meta = response_data.get('_meta', {})
        usage = response_data.get('usage', {})
        usage_details = usage.get('input_token_details', {})
        
        return {
            'run_uuid': str(uuid.uuid4()),
            'text': text.strip(),
            'logprobs': response_data.get('logprobs'),
            'model': meta.get('model'),
            'detect_model': meta.get('detect_model'),
            'source_file': meta.get('source_file'),
            'forced_language': meta.get('forced_language', False),
            'language_routing_enabled': meta.get('language_routing_enabled', False),
            'routed_language': meta.get('routed_language'),
            'probe_seconds': meta.get('probe_seconds'),
            'ffmpeg_used': meta.get('ffmpeg_used', False),
            'usage_type': usage.get('type'),
            'input_tokens': usage.get('input_tokens'),
            'output_tokens': usage.get('output_tokens'),
            'total_tokens': usage.get('total_tokens'),
            'audio_tokens': usage_details.get('audio_tokens'),
            'text_tokens': usage_details.get('text_tokens'),
            'response_json': json.dumps(response_data)  # Store full response as JSON
        }
    
    def upsert_source_file(self, conn, file_path: str) -> int:
        """
        Upsert a source file record and return its ID.
        
        Args:
            conn: Database connection
            file_path (str): Path to the source file
            
        Returns:
            int: Source file ID
        """
        with conn.cursor() as cursor:
            # Try to insert, handle unique constraint violation
            cursor.execute("""
                INSERT INTO gdr_source_file (path) 
                VALUES (%s) 
                ON CONFLICT (path) DO UPDATE SET path = EXCLUDED.path
                RETURNING id
            """, (file_path,))
            
            result = cursor.fetchone()
            source_file_id = result['id'] if result else None
            
            if source_file_id is None:
                # Fallback: select existing record
                cursor.execute("SELECT id FROM gdr_source_file WHERE path = %s", (file_path,))
                result = cursor.fetchone()
                source_file_id = result['id'] if result else None
            
            self.logger.debug(f"Source file ID for '{file_path}': {source_file_id}")
            return source_file_id
    
    def insert_diary_entry(self, conn, text: str, title: Optional[str] = None, 
                          mood: Optional[str] = None, tags: Optional[List[str]] = None) -> int:
        """
        Insert a diary entry and return its ID.
        
        Args:
            conn: Database connection
            text (str): Diary entry text
            title (Optional[str]): Diary entry title
            mood (Optional[str]): Diary entry mood
            tags (Optional[List[str]]): Diary entry tags
            
        Returns:
            int: Diary entry ID
        """
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO gdr_diary (title, text, mood, tags)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (title, text, mood, tags))
            
            result = cursor.fetchone()
            diary_id = result['id']
            
            self.logger.debug(f"Inserted diary entry with ID: {diary_id}")
            return diary_id
    
    def insert_transcription_run(self, conn, diary_id: int, source_file_id: Optional[int],
                               parsed_data: Dict[str, Any]) -> int:
        """
        Insert a transcription run record and return its ID.
        
        Args:
            conn: Database connection
            diary_id (int): Diary entry ID
            source_file_id (Optional[int]): Source file ID
            parsed_data (Dict[str, Any]): Parsed transcription data
            
        Returns:
            int: Transcription run ID
        """
        with conn.cursor() as cursor:
            run_uuid_value = parsed_data.get('run_uuid') or str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO gdr_transcription_run (
                    diary_id, run_uuid, source_file_id, model, detect_model,
                    forced_language, language_routing_enabled, routed_language,
                    probe_seconds, ffmpeg_used, logprobs_present, response_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                diary_id, run_uuid_value, source_file_id, parsed_data['model'], parsed_data['detect_model'],
                parsed_data['forced_language'], parsed_data['language_routing_enabled'],
                parsed_data['routed_language'], parsed_data['probe_seconds'],
                parsed_data['ffmpeg_used'], parsed_data['logprobs'] is not None,
                parsed_data['response_json']
            ))
            
            result = cursor.fetchone()
            run_id = result['id']
            
            self.logger.debug(f"Inserted transcription run with ID: {run_id}")
            return run_id
    
    def insert_transcription_usage(self, conn, run_id: int, parsed_data: Dict[str, Any]) -> int:
        """
        Insert a transcription usage record and return its ID.
        
        Args:
            conn: Database connection
            run_id (int): Transcription run ID
            parsed_data (Dict[str, Any]): Parsed transcription data
            
        Returns:
            int: Transcription usage ID
        """
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO gdr_transcription_usage (
                    run_id, type, input_tokens, output_tokens, total_tokens,
                    audio_tokens, text_tokens
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                run_id, parsed_data['usage_type'], parsed_data['input_tokens'],
                parsed_data['output_tokens'], parsed_data['total_tokens'],
                parsed_data['audio_tokens'], parsed_data['text_tokens']
            ))
            
            result = cursor.fetchone()
            usage_id = result['id']
            
            self.logger.debug(f"Inserted transcription usage with ID: {usage_id}")
            return usage_id
    
    def ingest_transcription(self, response_data: Union[str, Dict], 
                           title: Optional[str] = None,
                           mood: Optional[str] = None,
                           tags: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Ingest a complete transcription response into the database.
        
        This method handles the full ingestion process:
        1. Parse the transcription response
        2. Upsert source file record
        3. Insert diary entry
        4. Insert transcription run
        5. Insert usage information
        
        All operations are wrapped in a single transaction.
        
        Args:
            response_data (Union[str, Dict]): Transcription response data
            title (Optional[str]): Diary entry title
            mood (Optional[str]): Diary entry mood
            tags (Optional[List[str]]): Diary entry tags
            
        Returns:
            Dict[str, int]: Dictionary with IDs of created records
            
        Raises:
            ValueError: If response data is invalid
            psycopg2.Error: If there's a database error
        """
        self.logger.info("Starting transcription ingestion")
        
        # Parse the response data
        parsed_data = self.parse_transcription_response(response_data)
        self.logger.debug(f"Parsed transcription data for text: '{parsed_data['text'][:100]}...'")
        
        # Ingest within a transaction
        with self.db_manager.transaction() as conn:
            # Upsert source file
            source_file_id = None
            if parsed_data['source_file']:
                source_file_id = self.upsert_source_file(conn, parsed_data['source_file'])
            
            # Insert diary entry
            diary_id = self.insert_diary_entry(conn, parsed_data['text'], title, mood, tags)
            
            # Insert transcription run
            run_id = self.insert_transcription_run(conn, diary_id, source_file_id, parsed_data)
            
            # Insert usage information
            usage_id = self.insert_transcription_usage(conn, run_id, parsed_data)
            
            result = {
                'diary_id': diary_id,
                'source_file_id': source_file_id,
                'run_id': run_id,
                'usage_id': usage_id
            }
            
            self.logger.info(f"Transcription ingestion completed successfully: {result}")
            return result


# Convenience functions for common operations
def get_db_manager() -> DatabaseManager:
    """Get a configured database manager instance."""
    return DatabaseManager()


def get_transcription_ingestion() -> TranscriptionIngestion:
    """Get a configured transcription ingestion handler."""
    return TranscriptionIngestion()
