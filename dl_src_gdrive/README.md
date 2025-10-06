# Google Drive File Downloader

A Python application for downloading audio, text, and other files from Google Drive with OAuth2 authentication, configurable folder search, and comprehensive logging.

## Features

- **OAuth2 Authentication**: Secure Google Drive API access with automatic token refresh
- **Configurable Search**: Download from root directory or specific Google Drive folders
- **Multi-Type File Support**: Download audio files (MP3, M4A, WAV, OGG, FLAC, AAC, WMA), text files (TXT, DOCX, PDF), and other custom file types
- **Chronological Organization**: Files are organized in sequence-numbered directories
- **Selective Deletion**: Delete specific file types from Google Drive after successful download
- **Comprehensive Logging**: Detailed logging with configurable levels and file rotation
- **Environment Configuration**: Full .env file support with environment variable fallbacks
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Drive API credentials (client secret JSON file)

### Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd dl_src_gdrive
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Drive API credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth2 credentials (Desktop application)
   - Download the client secret JSON file
   - Rename it to `client_secret.json` and place it in the `config/` directory

4. **Configure the application**
   ```bash
   # Copy the example configuration
   cp .env.example .env
   
   # Edit .env with your settings
   notepad .env  # Windows
   nano .env     # Linux/macOS
   ```

5. **Run the application**
   ```bash
   python -m dl_src_gdrive.main
   ```

## Configuration

### Environment Variables

The application supports configuration through environment variables or a `.env` file. See `.env.example` for all available options:

#### Required Settings
- `DOWNLOAD_DIR`: Absolute path where audio files will be saved
- `CLIENT_SECRET_FILE`: Path to your Google Drive API client secret file

#### Optional Settings
- `SEARCH_FOLDERS`: Comma-separated list of Google Drive folder IDs (default: "root")
- `ALLOWED_AUDIO_EXTENSIONS`: Comma-separated list of audio file extensions to download
- `ALLOWED_TEXT_EXTENSIONS`: Comma-separated list of text file extensions to download
- `ALLOWED_OTHER_EXTENSIONS`: Comma-separated list of other file extensions to download
- `DELETE_AUDIO_FROM_SRC`: Whether to delete audio files from Google Drive after download (true/false)
- `DELETE_TEXT_FROM_SRC`: Whether to delete text files from Google Drive after download (true/false)
- `DELETE_OTHER_FROM_SRC`: Whether to delete other files from Google Drive after download (true/false)
- `DELETE_FROM_SRC`: Legacy setting - applies to all file types (true/false)
- `TOKEN_FILE`: Path to store OAuth2 token file

### Example Configuration

```env
# Download directory (must be absolute path)
DOWNLOAD_DIR=C:\Users\username\Downloads

# Google Drive API settings
CLIENT_SECRET_FILE=config/client_secret.json
TOKEN_FILE=config/token.json

# Search settings
SEARCH_FOLDERS=root,1ABC123DEF456
ALLOWED_AUDIO_EXTENSIONS=.mp3,.m4a,.wav
ALLOWED_TEXT_EXTENSIONS=.txt,.docx,.pdf
ALLOWED_OTHER_EXTENSIONS=.zip,.rar

# Behavior settings
DELETE_AUDIO_FROM_SRC=true
DELETE_TEXT_FROM_SRC=false
DELETE_OTHER_FROM_SRC=false
```

## Usage

### Basic Usage

```bash
# Download all file types from configured folders
python -m dl_src_gdrive.main

# Download only audio and text files (skip other files)
python -m dl_src_gdrive.main --skip-other

# Download only text files
python -m dl_src_gdrive.main --skip-audio --skip-other

# Enable debug logging
python -m dl_src_gdrive.main --debug

# Delete specific file types from Google Drive after download
python -m dl_src_gdrive.main --delete-audio --delete-text

# Clean up credentials after download (for security)
python -m dl_src_gdrive.main --cleanup
```

### Command Line Options

- `--debug`: Enable debug logging for detailed output
- `--cleanup`: Remove stored credentials after download
- `--skip-audio`: Skip downloading audio files
- `--skip-text`: Skip downloading text files
- `--skip-other`: Skip downloading other files
- `--delete-audio`: Delete audio files from Google Drive after successful download
- `--delete-text`: Delete text files from Google Drive after successful download
- `--delete-other`: Delete other files from Google Drive after successful download
- `--delete-from-gdrive`: Legacy option - delete all files from Google Drive after successful download

### Programmatic Usage

```python
from dl_src_gdrive.dl_gdrive_core.dl_src_gdrive import GoogleDriveDownloader

# Initialize downloader
downloader = GoogleDriveDownloader()

# Authenticate
if downloader.authenticate():
    # Download all file types
    results = downloader.download_all_files()
    print(f"Downloaded {sum(successful for successful, _ in results.values())} files total")
    
    # Or download specific file types
    results = downloader.download_all_files(
        download_audio=True,
        download_text=True,
        download_other=False
    )
    print(f"Audio: {results['audio'][0]}/{results['audio'][1]}")
    print(f"Text: {results['text'][0]}/{results['text'][1]}")
```

## Project Structure

```
dl_src_gdrive/
├── config/                          # Configuration files
│   ├── client_secret.json          # Google Drive API credentials
│   ├── token.json                  # OAuth2 token (auto-generated)
│   ├── dl_src_gdrive_config.py     # Google Drive configuration
│   └── proj_config.py              # Project-level configuration
├── src/dl_src_gdrive/              # Main application package
│   ├── dl_gdrive_core/             # Core downloader functionality
│   │   └── dl_src_gdrive.py        # GoogleDriveDownloader class
│   ├── main.py                     # CLI entry point
│   └── gdrive_logging.py           # Module-specific logging
├── utils/                          # Utility functions
│   └── file_sys_utils.py           # Path and file system utilities
├── logging_utils/                  # Centralized logging configuration
│   └── logging_config.py           # Logging setup and management
├── logs/                           # Log files (auto-created)
├── .env.example                    # Configuration template
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Supported File Formats

The application supports downloading files with these extensions:

### Audio Files (default)
- `.mp3` - MPEG Audio Layer III
- `.m4a` - MPEG-4 Audio
- `.wav` - Waveform Audio
- `.ogg` - Ogg Vorbis
- `.flac` - Free Lossless Audio Codec
- `.aac` - Advanced Audio Coding
- `.wma` - Windows Media Audio

### Text Files (default)
- `.txt` - Plain text files
- `.docx` - Microsoft Word documents
- `.pdf` - Portable Document Format

### Other Files
- Configurable via `ALLOWED_OTHER_EXTENSIONS` environment variable
- Default: empty list (no other files downloaded)

## File Organization

Downloaded files are organized in sequence-numbered directories to maintain chronological order:

```
downloads/
├── 001_file_id_1/
│   └── audio_file_1.mp3
├── 002_file_id_2/
│   └── document_1.pdf
├── 003_file_id_3/
│   └── text_file_1.txt
└── 004_file_id_4/
    └── audio_file_2.m4a
```

## Logging

The application provides comprehensive logging with configurable levels:

- **Console Output**: Real-time progress and status messages
- **File Output**: Detailed logs saved to `logs/gdrive_downloader.log`
- **Log Rotation**: Automatic rotation when log files reach 10MB
- **Multiple Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Log Configuration

You can configure logging through environment variables:

```env
LOG_CONSOLE_LEVEL=DEBUG
LOG_FILE_LEVEL=INFO
LOG_CONSOLE_OUTPUT=true
LOG_FILE_OUTPUT=true
```

## Error Handling

The application includes comprehensive error handling:

- **Configuration Validation**: Checks for required files and valid paths
- **Network Error Handling**: Graceful handling of API and network issues
- **File System Errors**: Proper handling of disk space and permission issues
- **User-Friendly Messages**: Clear error messages with troubleshooting hints

## Security

- **OAuth2 Authentication**: Secure Google Drive API access
- **Token Management**: Automatic token refresh and optional cleanup
- **Credential Storage**: Tokens stored locally with proper file permissions
- **No Hardcoded Secrets**: All sensitive data configurable via environment variables

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify `client_secret.json` is valid and in the correct location
   - Check internet connection
   - Ensure Google Drive API is enabled in your Google Cloud project

2. **No Files Found**
   - Verify `SEARCH_FOLDERS` configuration
   - Check file permissions in Google Drive
   - Ensure files have supported audio extensions

3. **Download Failures**
   - Check disk space in download directory
   - Verify file permissions
   - Check network connection stability

4. **Configuration Errors**
   - Ensure `DOWNLOAD_DIR` is an absolute path
   - Verify all required files exist
   - Check `.env` file syntax

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python -m dl_src_gdrive.main --debug
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=dl_src_gdrive
```

### Code Style

The project follows PEP 8 style guidelines:

```bash
# Check code style
flake8 src/ config/ utils/ logging_utils/

# Auto-format code
black src/ config/ utils/ logging_utils/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For support and questions:

1. Check the troubleshooting section above
2. Review the logs for error details
3. Open an issue on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Log files (with sensitive data removed)
   - System information (OS, Python version)

## Changelog

### Version 1.0.0
- Initial release
- OAuth2 authentication with Google Drive API
- Configurable folder search and audio file filtering
- Comprehensive logging and error handling
- Environment variable configuration support
- Cross-platform compatibility
