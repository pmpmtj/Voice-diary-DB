"""
Database Configuration Module

This module provides database configuration management for the Gmail downloader application.
It loads PostgreSQL connection parameters from environment variables with .env file fallback,
following the project's configuration patterns.

Key Features:
- Environment variable priority with .env fallback
- Connection string builder
- Connection pool configuration
- Schema version tracking
- Type hints and documentation

Usage:
    from config.db_config import DB_CONFIG
    connection_string = DB_CONFIG.get_connection_string()
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue with environment variables only
    pass


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration settings."""
    
    # Connection parameters
    host: str = "localhost"
    port: int = 5432
    database: str = "gmail_data"
    username: str = "gmail_user"
    password: str = "your_password_here"
    
    # Connection pool settings
    max_connections: int = 10
    min_connections: int = 1
    connection_timeout: int = 30
    
    # Schema version for migrations
    schema_version: str = "1.0"
    
    def __post_init__(self):
        """Load configuration from environment variables after initialization."""
        self.host = os.getenv('DB_HOST', self.host)
        self.port = int(os.getenv('DB_PORT', str(self.port)))
        self.database = os.getenv('DB_NAME', self.database)
        self.username = os.getenv('DB_USER', self.username)
        self.password = os.getenv('DB_PASSWORD', self.password)
        
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', str(self.max_connections)))
        self.min_connections = int(os.getenv('DB_MIN_CONNECTIONS', str(self.min_connections)))
        self.connection_timeout = int(os.getenv('DB_CONNECTION_TIMEOUT', str(self.connection_timeout)))
        
        self.schema_version = os.getenv('DB_SCHEMA_VERSION', self.schema_version)
    
    def get_connection_string(self, include_database: bool = True) -> str:
        """
        Build PostgreSQL connection string.
        
        Args:
            include_database (bool): Whether to include database name in connection string
            
        Returns:
            str: PostgreSQL connection string
            
        Example:
            >>> conn_str = DB_CONFIG.get_connection_string()
            >>> print(conn_str)
            postgresql://gmail_user:password@localhost:5432/gmail_data
        """
        database_part = f"/{self.database}" if include_database else ""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}{database_part}"
    
    def get_connection_params(self) -> dict:
        """
        Get connection parameters as dictionary for psycopg2.
        
        Returns:
            dict: Connection parameters
            
        Example:
            >>> params = DB_CONFIG.get_connection_params()
            >>> print(params['host'])
            localhost
        """
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.username,
            'password': self.password,
            'connect_timeout': self.connection_timeout
        }
    
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate database configuration.
        
        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
            
        Example:
            >>> is_valid, error = DB_CONFIG.validate_config()
            >>> if not is_valid:
            ...     print(f"Config error: {error}")
        """
        if not self.host:
            return False, "Database host is required"
        
        if not self.database:
            return False, "Database name is required"
        
        if not self.username:
            return False, "Database username is required"
        
        if not self.password or self.password == "your_password_here":
            return False, "Database password must be set"
        
        if self.port <= 0 or self.port > 65535:
            return False, f"Invalid port number: {self.port}"
        
        if self.max_connections < 1:
            return False, f"Max connections must be >= 1, got: {self.max_connections}"
        
        if self.min_connections < 0 or self.min_connections > self.max_connections:
            return False, f"Min connections must be between 0 and {self.max_connections}"
        
        return True, None


# Global database configuration instance
# Import this in your scripts: from config.db_config import DB_CONFIG
DB_CONFIG = DatabaseConfig()


def get_db_config() -> DatabaseConfig:
    """
    Get the global database configuration instance.
    
    Returns:
        DatabaseConfig: Configured database settings
        
    Example:
        >>> config = get_db_config()
        >>> print(f"Connecting to: {config.host}:{config.port}")
    """
    return DB_CONFIG


if __name__ == "__main__":
    # Configuration validation and display
    print("Database Configuration:")
    print(f"Host: {DB_CONFIG.host}")
    print(f"Port: {DB_CONFIG.port}")
    print(f"Database: {DB_CONFIG.database}")
    print(f"Username: {DB_CONFIG.username}")
    print(f"Password: {'*' * len(DB_CONFIG.password)}")
    print(f"Max Connections: {DB_CONFIG.max_connections}")
    print(f"Schema Version: {DB_CONFIG.schema_version}")
    
    # Validate configuration
    is_valid, error = DB_CONFIG.validate_config()
    if is_valid:
        print("\n✓ Configuration is valid")
        print(f"Connection String: {DB_CONFIG.get_connection_string()}")
    else:
        print(f"\n✗ Configuration error: {error}")
