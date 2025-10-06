"""
Database Configuration Module

This module provides centralized database configuration for the GDrive transcription system.
It supports PostgreSQL database connections with environment variable and .env file fallback.

Key Features:
- PostgreSQL database configuration management
- Environment variable support (highest priority)
- .env file fallback support
- Connection parameter validation
- Production-ready configuration patterns
- Support for both development and production environments

Configuration Sources (in order of priority):
1. Environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
2. .env file (if python-dotenv is available)
3. Default values (development settings)

Author: [Your Name]
Date: [Current Date]
Version: 1.0.0
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional


@dataclass
class DatabaseConfig:
    """
    Database configuration class for PostgreSQL connections.
    
    This class handles database connection parameters with support for:
    - Environment variable overrides
    - .env file fallback
    - Configuration validation
    - Connection parameter generation
    
    Attributes:
        host (str): Database host address
        port (int): Database port number
        database (str): Database name
        user (str): Database username
        password (str): Database password
        sslmode (str): SSL mode for connection (default: 'prefer')
        connect_timeout (int): Connection timeout in seconds (default: 10)
    """
    
    # Default values (development settings)
    host: str = "localhost"
    port: int = 5432
    database: str = "diary_pj_db"
    user: str = "postgres"
    password: str = "postgres"
    sslmode: str = "prefer"
    connect_timeout: int = 10
    
    def __post_init__(self):
        """Load database settings from environment variables or .env file."""
        # Load from environment variables first (highest priority)
        self.host = os.getenv("DB_HOST", self.host)
        self.port = int(os.getenv("DB_PORT", self.port))
        self.database = os.getenv("DB_NAME", self.database)
        self.user = os.getenv("DB_USER", self.user)
        self.password = os.getenv("DB_PASSWORD", self.password)
        self.sslmode = os.getenv("DB_SSLMODE", self.sslmode)
        self.connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", self.connect_timeout))
        
        # Fall back to .env file if environment variables not set
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            # Re-check environment variables after loading .env
            self.host = os.getenv("DB_HOST", self.host)
            self.port = int(os.getenv("DB_PORT", self.port))
            self.database = os.getenv("DB_NAME", self.database)
            self.user = os.getenv("DB_USER", self.user)
            self.password = os.getenv("DB_PASSWORD", self.password)
            self.sslmode = os.getenv("DB_SSLMODE", self.sslmode)
            self.connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", self.connect_timeout))
        except ImportError:
            # python-dotenv not installed, continue with defaults/env vars
            pass
    
    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the database configuration.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
                - is_valid: True if configuration is valid, False otherwise
                - error_message: Error description if validation fails, None if valid
                
        Example:
            >>> is_valid, error = DB_CONFIG.validate_config()
            >>> if not is_valid:
            ...     print(f"Configuration error: {error}")
        """
        # Check required fields
        if not self.host:
            return False, "Database host is required"
        
        if not self.database:
            return False, "Database name is required"
        
        if not self.user:
            return False, "Database user is required"
        
        if not self.password:
            return False, "Database password is required"
        
        # Validate port range
        if not (1 <= self.port <= 65535):
            return False, f"Database port must be between 1 and 65535, got {self.port}"
        
        # Validate SSL mode
        valid_ssl_modes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']
        if self.sslmode not in valid_ssl_modes:
            return False, f"Invalid SSL mode '{self.sslmode}'. Must be one of: {valid_ssl_modes}"
        
        # Validate timeout
        if self.connect_timeout <= 0:
            return False, f"Connection timeout must be positive, got {self.connect_timeout}"
        
        return True, None
    
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters for psycopg2.connect().
        
        Returns:
            Dict[str, Any]: Dictionary of connection parameters suitable for psycopg2
            
        Example:
            >>> import psycopg2
            >>> conn = psycopg2.connect(**DB_CONFIG.get_connection_params())
        """
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'sslmode': self.sslmode,
            'connect_timeout': self.connect_timeout
        }
    
    def get_connection_string(self) -> str:
        """
        Get PostgreSQL connection string.
        
        Returns:
            str: PostgreSQL connection string
            
        Example:
            >>> conn_str = DB_CONFIG.get_connection_string()
            >>> print(conn_str)
            postgresql://user:password@localhost:5432/database
        """
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def __str__(self) -> str:
        """String representation of database configuration (password masked)."""
        return (f"DatabaseConfig(host='{self.host}', port={self.port}, "
                f"database='{self.database}', user='{self.user}', "
                f"password='***', sslmode='{self.sslmode}', "
                f"connect_timeout={self.connect_timeout})")
    
    def __repr__(self) -> str:
        """Detailed string representation of database configuration."""
        return self.__str__()


# Global database configuration instance
DB_CONFIG = DatabaseConfig()


def get_db_config() -> DatabaseConfig:
    """
    Get the global database configuration instance.
    
    Returns:
        DatabaseConfig: The global database configuration instance
        
    Example:
        >>> config = get_db_config()
        >>> print(f"Connecting to {config.host}:{config.port}")
    """
    return DB_CONFIG


def test_connection() -> Tuple[bool, Optional[str]]:
    """
    Test database connection using current configuration.
    
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
            - success: True if connection successful, False otherwise
            - error_message: Error description if connection fails, None if successful
            
    Example:
        >>> success, error = test_connection()
        >>> if success:
        ...     print("Database connection successful")
        ... else:
        ...     print(f"Connection failed: {error}")
    """
    try:
        import psycopg2
        
        # Validate configuration first
        is_valid, error = DB_CONFIG.validate_config()
        if not is_valid:
            return False, f"Configuration error: {error}"
        
        # Test connection
        with psycopg2.connect(**DB_CONFIG.get_connection_params()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                return True, f"Connected successfully to PostgreSQL: {version}"
                
    except ImportError:
        return False, "psycopg2 not installed. Please install with: pip install psycopg2-binary"
    except Exception as e:
        return False, f"Connection failed: {e}"


if __name__ == "__main__":
    """
    Test the database configuration when run directly.
    """
    print("Database Configuration Test")
    print("=" * 40)
    print(f"Configuration: {DB_CONFIG}")
    
    # Test configuration validation
    is_valid, error = DB_CONFIG.validate_config()
    print(f"Configuration valid: {is_valid}")
    if not is_valid:
        print(f"Error: {error}")
        exit(1)
    
    # Test connection
    print("\nTesting database connection...")
    success, message = test_connection()
    print(f"Connection test: {'SUCCESS' if success else 'FAILED'}")
    if message:
        print(f"Message: {message}")
    
    if success:
        print("\nDatabase configuration is working correctly!")
    else:
        print("\nDatabase configuration needs attention.")
        exit(1)
