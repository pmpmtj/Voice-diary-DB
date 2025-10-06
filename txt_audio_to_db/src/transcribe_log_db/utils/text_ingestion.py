"""
Text document ingestion utilities.

Handle ingestion of text documents (.txt, .docx, .pdf) into the database,
creating diary entries and tracking source files with stub transcription records.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the path to import the config
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .db_utils import get_db_manager
from common.logging_utils.logging_config import get_logger
from ..core.text_extractor import extract_text_content


class TextIngestion:
    """
    Handle ingestion of text documents into the database.
    
    Creates diary entries from text content and maintains referential integrity
    by creating stub transcription run records.
    """
    
    def __init__(self):
        """Initialize the text ingestion handler."""
        self.db_manager = get_db_manager()
        self.logger = get_logger("text_ingestion")
        self.logger.debug("Text ingestion handler initialized")
    
    def ingest_text_document(self, file_path: Path, 
                           mood: Optional[str] = None, 
                           tags: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Ingest a text document into the database.
        
        Args:
            file_path (Path): Path to the text document
            mood (Optional[str]): Mood for the diary entry
            tags (Optional[List[str]]): Tags for the diary entry
            
        Returns:
            Dict[str, int]: Dictionary containing:
                - diary_id: ID of created diary entry
                - source_file_id: ID of source file record
                - run_id: ID of transcription run record (stub)
                - usage_id: Always None (no usage tracking for text)
        """
        self.logger.info(f"Starting text document ingestion: {file_path.name}")
        
        try:
            # Extract text content
            extracted_data = extract_text_content(file_path)
            
            if not extracted_data["text"].strip():
                self.logger.warning(f"No text content extracted from {file_path.name}")
                # Still create a diary entry with empty text to maintain consistency
                extracted_data["text"] = f"[No text content extracted from {file_path.name}]"
            
            self.logger.debug(f"Extracted text: '{extracted_data['text'][:100]}...'")
            self.logger.debug(f"Extracted title: '{extracted_data['title']}'")
            
            # Ingest within a transaction
            with self.db_manager.transaction() as conn:
                # Upsert source file
                source_file_id = self._upsert_source_file(conn, extracted_data["source_file"])
                
                # Insert diary entry
                diary_id = self._insert_diary_entry(
                    conn, 
                    extracted_data["text"], 
                    extracted_data["title"], 
                    mood, 
                    tags
                )
                
                # Insert stub transcription run
                run_id = self._insert_stub_transcription_run(
                    conn, 
                    diary_id, 
                    source_file_id, 
                    extracted_data
                )
                
                result = {
                    'diary_id': diary_id,
                    'source_file_id': source_file_id,
                    'run_id': run_id,
                    'usage_id': None  # No usage tracking for text documents
                }
                
                self.logger.info(f"Text document ingestion completed successfully: {result}")
                return result
                
        except Exception as e:
            self.logger.error(f"Failed to ingest text document {file_path}: {e}")
            raise
    
    def _upsert_source_file(self, conn, file_path: str) -> int:
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
    
    def _insert_diary_entry(self, conn, text: str, title: str, 
                          mood: Optional[str] = None, 
                          tags: Optional[List[str]] = None) -> int:
        """
        Insert a diary entry and return its ID.
        
        Args:
            conn: Database connection
            text (str): Diary entry text
            title (str): Diary entry title
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
    
    def _insert_stub_transcription_run(self, conn, diary_id: int, source_file_id: int,
                                     extracted_data: Dict[str, Any]) -> int:
        """
        Insert a stub transcription run record to maintain referential integrity.
        
        Args:
            conn: Database connection
            diary_id (int): Diary entry ID
            source_file_id (int): Source file ID
            extracted_data (Dict[str, Any]): Extracted text data
            
        Returns:
            int: Transcription run ID
        """
        with conn.cursor() as cursor:
            # Create a minimal response JSON for text documents
            import json
            response_json = json.dumps({
                "text": extracted_data["text"],
                "source_file": extracted_data["source_file"],
                "file_type": extracted_data["file_type"],
                "ingestion_type": "text_document"
            })
            
            cursor.execute("""
                INSERT INTO gdr_transcription_run (
                    diary_id, run_uuid, source_file_id, model, detect_model,
                    forced_language, language_routing_enabled, routed_language,
                    probe_seconds, ffmpeg_used, logprobs_present, response_json
                )
                VALUES (%s, gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                diary_id,
                source_file_id,
                f"text_extractor_{extracted_data['file_type']}",  # model
                None,  # detect_model
                None,  # forced_language
                None,  # language_routing_enabled
                None,  # routed_language
                None,  # probe_seconds
                None,  # ffmpeg_used
                None,  # logprobs_present
                response_json
            ))
            
            result = cursor.fetchone()
            run_id = result['id']
            
            self.logger.debug(f"Inserted stub transcription run with ID: {run_id}")
            return run_id


# Convenience function for common operations
def get_text_ingestion() -> TextIngestion:
    """Get a configured text ingestion handler instance."""
    return TextIngestion()
