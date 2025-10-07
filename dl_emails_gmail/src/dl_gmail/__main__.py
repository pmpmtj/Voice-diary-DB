"""
Gmail Downloader Package Entry Point

This module allows the dl_gmail package to be run as a module using:
    python -m src.dl_gmail

It runs the main Gmail message processing functionality.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.dl_gmail.dl_gmail import main

if __name__ == "__main__":
    main()
