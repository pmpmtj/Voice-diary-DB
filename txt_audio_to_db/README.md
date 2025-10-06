# Transcription Logging Application

A Python application for logging transcription data into a normalized PostgreSQL database schema. This application takes transcription JSON responses and stores them in a structured database with proper relationships and metadata tracking.

## Features

- **Normalized Database Schema**: Stores transcription data across multiple related tables
- **1:1 Relationship**: Each diary entry has exactly one transcription run
- **Full Metadata Preservation**: Retains complete API response for auditing/debugging
- **Transaction Safety**: All operations wrapped in database transactions
- **Comprehensive Logging**: Detailed logging throughout the application
- **Configuration Management**: Environment variable and .env file support
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Audio Discovery**: Automatically finds and processes audio files in UUID-named folders
- **Text Document Processing**: Processes .txt, .docx, and .pdf files with text extraction
- **Integrated Transcription**: Uses local transcription module for direct audio processing
- **Sequential Processing**: Audio processing followed by text document processing
- **Batch Processing**: Process single files or all unprocessed files
- **Idempotency**: Run UUID tracking prevents duplicate processing
- **PDF Error Handling**: Graceful handling of PDF extraction failures with clear logging

## Database Schema

The application creates four main tables:

### `diary`
- Stores the main diary entries with transcription text
- Fields: `id`, `uuid`, `created_at`, `title`, `text`, `revised_text`, `mood`, `tags`, `updated_at`

### `source_file`
- Tracks source audio and text files
- Fields: `id`, `path`, `file_id`, `file_hash`, `created_at`

### `transcription_run`
- Stores transcription metadata and full API response
- Fields: `id`, `diary_id` (FK), `run_uuid` (unique), `source_file_id` (FK), model info, language settings, processing flags, `response_json`, timestamps

### `transcription_usage`
- Tracks token usage information
- Fields: `id`, `run_id` (FK), token counts, `created_at`

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL Database**:
   - Install PostgreSQL
   - Create a database (default: `diary_pj_db`)
   - Configure connection settings

3. **Configure Database Connection**:
   
   **Option A: Environment Variables**
   ```bash
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=diary_pj_db
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   ```
   
   **Option B: .env File**
   ```bash
   # Create .env file in project root
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=diary_pj_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

4. **Configure Download Directory**:
   - Set `download_dir` in `config/proj_config.py` to your files location
   - Audio and text files should be organized in UUID-named subfolders (one file per folder)
   - Supported file types: `.mp3`, `.m4a`, `.wav` (audio), `.txt`, `.docx`, `.pdf` (text)

## Usage

### Command Line Interface

**Initialize database only**:
```bash
cd src
python -m transcribe_log_db.main --init-only
```

**Process newest unprocessed audio file** (default behavior):
```bash
cd src
python -m transcribe_log_db.main --title "Auto Entry" --mood "note"
```

**Process all unprocessed files**:
```bash
cd src
python -m transcribe_log_db.main --batch
```

**Process text documents only**:
```bash
cd src
python -m transcribe_log_db.main --text-only --batch
```

**Process specific audio file**:
```bash
cd src
python -m transcribe_log_db.main --audio /path/to/audio.m4a --title "My Recording" --mood "happy"
```

**Ingest from JSON file**:
```bash
cd src
python -m transcribe_log_db.main --input example_output.json
```

**Use custom download directory**:
```bash
cd src
python -m transcribe_log_db.main --audio-dir /path/to/files/folder --batch
```

**Force reprocess (ignore already processed files)**:
```bash
cd src
python -m transcribe_log_db.main --reprocess --batch
```

### Programmatic Usage

```python
from transcribe_log_db.utils import get_db_manager, get_transcription_ingestion
from transcribe_audio.core.transcription import transcribe_audio

# Initialize database
db_manager = get_db_manager()
db_manager.initialize_database()

# Set up ingestion
ingestion_handler = get_transcription_ingestion()

# Transcribe audio file
audio_result = transcribe_audio("/path/to/audio.m4a")

# Ingest transcription data
result = ingestion_handler.ingest_transcription(
    audio_result,
    title="My Recording",
    mood="content",
    tags=["work", "meeting"]
)

print(f"Diary ID: {result['diary_id']}")
print(f"Run ID: {result['run_id']}")
print(f"Run UUID: {result.get('run_uuid')}")
```

### Text Document Processing

The application can process text documents directly without transcription:

```python
from transcribe_log_db.utils.text_ingestion import get_text_ingestion

# Initialize text ingestion
text_handler = get_text_ingestion()

# Process a text document
result = text_handler.ingest_text_document(
    "/path/to/document.txt",
    mood="reading",
    tags=["document", "notes"]
)

print(f"Diary ID: {result['diary_id']}")
print(f"Source File ID: {result['source_file_id']}")
```

**Supported Text Formats**:
- **TXT files**: Plain text with UTF-8 encoding (with BOM handling)
- **DOCX files**: Microsoft Word documents (extracts paragraphs)
- **PDF files**: PDF documents (with error handling for corrupted files)

**Text Processing Features**:
- Automatic title extraction from first line (truncated to 255 characters)
- Robust encoding detection for text files
- Graceful PDF error handling with clear logging
- Same database schema as audio transcriptions
- Batch processing support

### Example Usage Script

Run the included example:
```bash
python example_usage.py
```

## Input Format

The application expects JSON responses in this format:

```json
{
    "text": "Transcribed text content",
    "logprobs": null,
    "usage": {
        "input_tokens": 126,
        "output_tokens": 23,
        "total_tokens": 149,
        "type": "tokens",
        "input_token_details": {
            "audio_tokens": 126,
            "text_tokens": 0
        }
    },
    "_meta": {
        "model": "gpt-4o-transcribe",
        "detect_model": "gpt-4o-mini-transcribe",
        "source_file": "/path/to/audio/file.m4a",
        "forced_language": false,
        "language_routing_enabled": false,
        "routed_language": null,
        "probe_seconds": 25,
        "ffmpeg_used": false
    }
}
```

## Project Structure

```
transcription_to_db/
├── config/
│   └── proj_config.py         # Project configuration
├── database/
│   └── gdrive_schema.sql      # Database schema
├── logging_utils/
│   └── logging_config.py      # Logging configuration
├── src/
│   ├── transcribe_log_db/     # Main logging application
│   │   ├── core/
│   │   │   └── text_extractor.py # Text extraction utilities
│   │   ├── utils/             # Utility modules
│   │   │   ├── audio_finder.py   # Audio discovery utilities
│   │   │   ├── text_finder.py    # Text document discovery utilities
│   │   │   ├── text_ingestion.py # Text document ingestion
│   │   │   └── db_utils.py       # Database utilities
│   │   └── main.py            # Main application entry point
│   └── transcribe_audio/      # Local transcription module
│       └── core/
│           └── transcription.py # Transcription functions
├── example_output.json        # Example transcription data
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Logging

The application provides comprehensive logging with:
- Console output for real-time monitoring
- File output for persistent logs
- Configurable log levels
- Module-specific loggers

Log files are stored in the `logs/` directory by default.

## Error Handling

- Database transactions with automatic rollback on errors
- Comprehensive error logging
- Graceful handling of missing files and invalid data
- Connection management with automatic cleanup

## Development

The application follows these architectural principles:
- **Modular Design**: Separate concerns into focused modules
- **Configuration-driven**: Centralized configuration management
- **Production-ready**: Proper error handling and logging
- **Cross-platform**: OS-agnostic code with proper path handling
- **Self-contained**: Modules handle their own dependencies

## Dependencies

- `psycopg2-binary`: PostgreSQL database adapter
- `python-dotenv`: Environment variable loading (optional)
- `openai`: OpenAI API client for transcription
- `python-docx`: Microsoft Word document processing
- `PyPDF2`: PDF document processing

## File Organization

The application expects files to be organized in UUID-named subfolders:

```
downloads/
├── 1FNUSHfO8fb4DgDRGhSuV1k0dfbhNpuCg/
│   ├── audio_file.m4a
│   └── document.txt
├── 1j4qyL6HM4ZLY0opKxGLc_KVaC5JcJsbQ/
│   ├── audio_file.mp3
│   └── report.pdf
└── ...
```

Each UUID folder can contain:
- **Audio files**: `.mp3`, `.m4a`, `.wav` (for transcription)
- **Text files**: `.txt`, `.docx`, `.pdf` (for direct text extraction)

The application will:
1. **Audio Processing**: Discover audio files, transcribe them, and save `transcript.json` in the same UUID folder
2. **Text Processing**: Discover text files, extract text content, and create diary entries
3. **Database Integration**: Ingest all results into the database with proper relationships
4. **Duplicate Prevention**: Check if files have been processed before (based on file path in database)

## CLI Flags

- `--audio PATH`: Process specific audio file
- `--audio-dir PATH`: Override default download directory
- `--batch`: Process all unprocessed files (default: newest only)
- `--reprocess`: Ignore database check and reprocess files
- `--text-only`: Skip audio processing and only process text documents
- `--input PATH`: Ingest from JSON file instead of processing files
- `--title TEXT`: Set diary entry title
- `--mood TEXT`: Set diary entry mood
- `--tags TEXT...`: Set diary entry tags
- `--init-only`: Only initialize database, don't process files

## License

[Add your license information here]
