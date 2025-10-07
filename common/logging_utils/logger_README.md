# Universal Logging System

This directory contains a universal logging configuration system that provides centralized logging management with log rotation for any Python project.
 
## Features

- **Universal Configuration**: Works for any Python project, not just specific ones
- **Log Rotation**: Size-based rotation (10MB max, 7 backups) to prevent oversized log files
- **Flexible Configuration**: Global defaults with per-logger overrides
- **Frozen Execution Support**: Handles both normal Python execution and PyInstaller bundles
- **Consistent Formatting**: Standardized log message format across all modules
- **Easy Module Integration**: Simple per-module helper files for quick adoption

## Quick Start

### 1. Basic Usage

```python
from logging_utils.logging_config import get_logger

# Get a logger (uses defaults)
logger = get_logger("my_module")
logger.info("This is an info message")
logger.debug("This is a debug message")
```

### 2. Per-Module Helper Pattern

Create a `logging.py` file in your module directory:

```python
# src/my_module/logging.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from logging_utils.logging_config import get_logger as _get_logger

# Module logger
logger = _get_logger("my_module")

# Convenience functions
def debug(message, *args, **kwargs):
    logger.debug(message, *args, **kwargs)

def info(message, *args, **kwargs):
    logger.info(message, *args, **kwargs)

# ... etc for warning, error, critical

__all__ = ['logger', 'debug', 'info', 'warning', 'error', 'critical']
```

Then use in your module:

```python
# src/my_module/main.py
from .logging import logger, info, debug

logger.info("Starting application...")
debug("Detailed debug information")
```

## Configuration

### Global Configuration

Edit `logging_utils/logging_config.py` to customize global defaults:

```python
LOGGING_CONFIG = {
    "defaults": {
        "console_level": "DEBUG",        # Console log level
        "file_level": "INFO",            # File log level
        "console_output": True,          # Enable console logging
        "file_output": True,             # Enable file logging
        "rotation": {
            "mode": "size",
            "max_bytes": 10 * 1024 * 1024,  # 10MB
            "backup_count": 7
        },
        "log_dir": None  # Uses SCRIPT_DIR/logging
    },
    "loggers": {
        # Per-logger overrides
        "my_module": {
            "file_level": "DEBUG",
            "log_filename": "my_module.log"
        }
    },
    "strict_config": False  # Set to True to require all loggers in config
}
```

### Per-Logger Overrides

You can override any default setting for specific loggers:

```python
"loggers": {
    "my_module": {
        "console_level": "INFO",         # Override console level
        "file_level": "DEBUG",           # Override file level
        "log_filename": "custom.log",    # Custom log filename
        "console_output": False,         # Disable console for this logger
        "rotation": {
            "max_bytes": 5 * 1024 * 1024,  # 5MB for this logger
            "backup_count": 3
        }
    }
}
```

## Log File Locations

- **Default**: `SCRIPT_DIR/logging/`
- **Frozen (PyInstaller)**: `executable_directory/logging/`
- **Normal Python**: `project_root/logging/`

## Log Rotation

- **Trigger**: When log file reaches `max_bytes` (default: 10MB)
- **Backup Count**: Number of rotated files to keep (default: 7)
- **Naming**: `filename.log`, `filename.log.1`, `filename.log.2`, etc.
- **Compression**: Not enabled by default (can be added if needed)

## Advanced Usage

### Custom Log Directory

```python
from pathlib import Path
from logging_utils.logging_config import get_logger

# Use custom log directory
logger = get_logger("my_module", log_dir=Path("/custom/log/path"))
```

### Runtime Level Changes

```python
from logging_utils.logging_config import set_console_level

# Change console level at runtime
set_console_level(logger, "INFO")
```

### Strict Configuration Mode

Set `strict_config: True` to require all loggers to be explicitly configured:

```python
LOGGING_CONFIG = {
    "strict_config": True,
    "loggers": {
        "allowed_logger_1": {...},
        "allowed_logger_2": {...}
    }
}
```

## Migration from Old System

If you have existing code using the old logging system:

1. **Old way**:
   ```python
   from logging_utils.logging_config import get_logger
   logger = get_logger("dl_config")
   ```

2. **New way** (same API, but with rotation):
   ```python
   from logging_utils.logging_config import get_logger
   logger = get_logger("dl_config")  # Now uses rotation!
   ```

3. **Or use per-module helper**:
   ```python
   from .logging import logger
   logger.info("Message")
   ```

## Troubleshooting

### Logger Not Found Warning

If you see: `WARNING: Logger 'unknown_logger' not in configuration, using defaults`

- **Solution 1**: Add the logger to `LOGGING_CONFIG["loggers"]`
- **Solution 2**: Set `strict_config: False` (default) to allow unknown loggers
- **Solution 3**: Use the logger name that matches your module structure

### Log Files Not Created

- Check that `file_output: True` in configuration
- Verify log directory permissions
- Ensure the logger is actually being used (loggers are created lazily)

### Rotation Not Working

- Verify `max_bytes` is reached (default: 10MB)
- Check file permissions in log directory
- Ensure `backup_count` is > 0

## Examples

See `src/dl_gmail/logging.py` for a complete example of the per-module helper pattern.
