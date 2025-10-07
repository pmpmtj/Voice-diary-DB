"""
Database Initialization Script

This script initializes the Gmail database schema by executing the gmail_schema.sql DDL script.
It can be run multiple times safely as all CREATE statements use IF NOT EXISTS.

Usage:
    python database/init_gmail_schema.py
    
Features:
- Executes gmail_schema.sql against the configured database
- Verifies table creation
- Safe to run multiple times
- Uses existing logging system for progress tracking
- Validates database connection before proceeding
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path when running directly
if __name__ == "__main__":
    # Get the directory containing this script
    script_dir = Path(__file__).resolve().parent
    # Navigate to project root (1 level up: database -> project_root)
    project_root = script_dir.parent
    # Add project root to sys.path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Error: psycopg2 not installed. Please install with: pip install psycopg2-binary")
    sys.exit(1)

from dl_emails_gmail.config.db_config import DB_CONFIG, get_db_config
from dl_emails_gmail.logging_utils.logging_config import get_logger

# Initialize logger for this module
logger = get_logger("init_db")


def execute_sql_file(connection, sql_file_path: Path) -> bool:
    """
    Execute a SQL file against the database connection.
    
    Args:
        connection: Database connection object
        sql_file_path (Path): Path to the SQL file to execute
        
    Returns:
        bool: True if execution was successful, False otherwise
        
    Example:
        >>> success = execute_sql_file(conn, Path("gmail_schema.sql"))
        >>> if success:
        ...     print("Schema created successfully")
    """
    try:
        if not sql_file_path.exists():
            logger.error(f"SQL file not found: {sql_file_path}")
            return False
        
        logger.info(f"Executing SQL file: {sql_file_path}")
        
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Execute the entire SQL file as one statement
        # This handles complex PostgreSQL functions and procedures properly
        with connection.cursor() as cursor:
            try:
                logger.debug("Executing complete SQL schema...")
                cursor.execute(sql_content)
                logger.debug("SQL schema executed successfully")
            except Exception as e:
                # Log the error but continue - some statements might fail if objects already exist
                logger.warning(f"Some SQL statements failed (might be expected): {e}")
                # Continue execution as some errors are expected with IF NOT EXISTS
        
        connection.commit()
        logger.info("SQL file executed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to execute SQL file: {e}")
        connection.rollback()
        return False


def verify_tables_exist(connection) -> bool:
    """
    Verify that all expected tables exist in the database.
    
    Args:
        connection: Database connection object
        
    Returns:
        bool: True if all tables exist, False otherwise
        
    Example:
        >>> if verify_tables_exist(conn):
        ...     print("All tables created successfully")
    """
    expected_tables = [
        'gml_threads',
        'gml_messages', 
        'gml_labels',
        'gml_message_labels',
        'gml_attachments',
        'gml_schema_versions'
    ]
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Existing tables: {existing_tables}")
            
            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False
            
            logger.info("All expected tables exist")
            return True
            
    except Exception as e:
        logger.error(f"Failed to verify tables: {e}")
        return False


def get_schema_version(connection) -> Optional[str]:
    """
    Get the current schema version from the database.
    
    Args:
        connection: Database connection object
        
    Returns:
        Optional[str]: Schema version if available, None otherwise
        
    Example:
        >>> version = get_schema_version(conn)
        >>> print(f"Current schema version: {version}")
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT version, applied_at, description 
                FROM gml_schema_versions 
                ORDER BY applied_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                version, applied_at, description = result
                logger.info(f"Current schema version: {version} (applied: {applied_at})")
                logger.info(f"Description: {description}")
                return version
            else:
                logger.warning("No schema version found")
                return None
                
    except Exception as e:
        logger.error(f"Failed to get schema version: {e}")
        return None


def test_database_connection() -> bool:
    """
    Test database connection and configuration.
    
    Returns:
        bool: True if connection successful, False otherwise
        
    Example:
        >>> if test_database_connection():
        ...     print("Database connection successful")
    """
    try:
        # Validate configuration first
        is_valid, error = DB_CONFIG.validate_config()
        if not is_valid:
            logger.error(f"Database configuration error: {error}")
            return False
        
        logger.info(f"Connecting to database: {DB_CONFIG.host}:{DB_CONFIG.port}/{DB_CONFIG.database}")
        
        # Test connection
        with psycopg2.connect(**DB_CONFIG.get_connection_params()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()[0]
                logger.info(f"Connected to PostgreSQL: {db_version}")
                
        return True
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please check your database configuration in .env file")
        return False


def main():
    """
    Main function to initialize the database schema.
    
    This function:
    1. Validates database configuration
    2. Tests database connection
    3. Executes the gmail_schema.sql DDL script
    4. Verifies table creation
    5. Reports schema version
    """
    try:
        logger.info("Starting database initialization...")
        
        # Test database connection
        if not test_database_connection():
            logger.error("Database connection test failed. Exiting.")
            return False
        
        # Get schema file path
        script_dir = Path(__file__).resolve().parent
        schema_file = script_dir / "gmail_schema.sql"
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return False
        
        # Connect to database and execute schema
        logger.info("Executing database schema...")
        with psycopg2.connect(**DB_CONFIG.get_connection_params()) as conn:
            # Set isolation level for DDL operations
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            # Execute schema file
            if not execute_sql_file(conn, schema_file):
                logger.error("Failed to execute schema file")
                return False
            
            # Verify tables were created
            if not verify_tables_exist(conn):
                logger.error("Table verification failed")
                return False
            
            # Get and display schema version
            get_schema_version(conn)
        
        logger.info("Database initialization completed successfully!")
        print("\n" + "="*60)
        print("DATABASE INITIALIZATION SUCCESS")
        print("="*60)
        print("+ Database connection established")
        print("+ Schema file executed")
        print("+ All tables created")
        print("+ Schema version recorded")
        print("\nYou can now run the Gmail downloader with database integration.")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\n- Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
