# Gmail Database Integration

This directory contains the database schema and initialization scripts for the Gmail downloader application.

## Overview

The database integration stores Gmail message data in PostgreSQL with support for:
- **Threads** (`gml_threads`): Email conversation tracking with message counts and timestamps
- **Messages** (`gml_messages`): Core email data (sender, subject, body, date, processing status)
- **Labels** (`gml_labels`): Gmail label management with many-to-many relationships
- **Attachments** (`gml_attachments`): Complete attachment metadata with file paths and download status
- **Relationships**: Proper foreign key relationships with cascading deletes

All tables use the `gml_` prefix for organization in multi-application databases.

## Files

- `gmail_schema.sql` - Complete database schema with tables, indexes, and views
- `init_gmail_schema.py` - Database initialization script
- `README.md` - This documentation file

## Quick Start

### 1. Install Dependencies

```bash
pip install psycopg2-binary
```

### 2. Configure Database

Edit the `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gmail_data
DB_USER=gmail_user
DB_PASSWORD=your_password_here
```

### 3. Initialize Database

Run the initialization script:

```bash
python database/init_gmail_schema.py
```

This will:
- Create all necessary tables (gml_threads, gml_messages, gml_labels, gml_message_labels, gml_attachments)
- Set up indexes for optimal query performance
- Create foreign key relationships with proper cascading
- Initialize the schema version tracking system
- Insert system labels (INBOX, SENT, etc.)
- Create helpful views for data analysis

### 4. Run Gmail Downloader

The Gmail downloader will now automatically save messages and download attachments to the database:

```bash
python -m src.dl_gmail
```

This will:
- Process emails matching your search query
- Download attachments to the configured directory
- Save all message data to the database
- Apply labels and update processing status

## Attachment Downloads

The system automatically downloads email attachments with the following features:

### Download Configuration

Edit `config/dl_gmail_config.py` to configure attachment downloads:

```python
# Attachment download settings
download_attachments: bool = True
attachment_download_dir: str = r"C:\Users\pmpmt\Downloads\gmail_attachments"
max_attachment_size: int = 10 * 1024 * 1024  # 10 MB
handle_duplicate_filenames: bool = True
```

### Download Location

Attachments are saved to: `{attachment_download_dir}/{YYYY-MM-DD}/`

Example structure:
```
C:\Users\pmpmt\Downloads\gmail_attachments\
├── 2025-10-05\
│   ├── document.pdf
│   ├── image_1.png
│   └── report_2.xlsx
└── 2025-10-06\
    └── presentation.pptx
```

### Features

- **Date-based Organization**: Files automatically organized by download date
- **Duplicate Handling**: Automatic `_1`, `_2` suffixes prevent overwrites
- **Filename Sanitization**: Removes unsafe characters for filesystem compatibility
- **Size Limits**: Respects configurable maximum file size (default: 10 MB)
- **Database Integration**: File paths stored in database for future reference
- **Error Handling**: Graceful handling of download failures without breaking email processing

## Database Schema

### Tables

#### `gml_threads`
- **thread_id** (VARCHAR): Gmail thread ID (primary key)
- **subject** (VARCHAR): Thread subject
- **message_count** (INTEGER): Number of messages in thread
- **last_message_date** (TIMESTAMP): Date of most recent message
- **metadata** (JSONB): Additional thread data

#### `gml_messages`
- **id** (UUID): Internal primary key
- **message_id** (VARCHAR): Gmail message ID (unique)
- **thread_id** (VARCHAR): Reference to gml_threads table
- **sender** (TEXT): Email sender
- **recipient** (TEXT): Email recipient
- **subject** (VARCHAR): Email subject
- **date** (TIMESTAMP): Email date
- **body_text** (TEXT): Plain text email body
- **processed_successfully** (BOOLEAN): Processing status
- **saved_to_db** (BOOLEAN): Database save status
- **metadata** (JSONB): Additional message data

#### `gml_labels`
- **label_id** (VARCHAR): Gmail label ID (primary key)
- **name** (VARCHAR): Label name
- **label_type** (VARCHAR): Label type (user/system)
- **metadata** (JSONB): Additional label data

#### `gml_message_labels`
- **message_id** (UUID): Reference to gml_messages table
- **label_id** (VARCHAR): Reference to gml_labels table
- **applied_at** (TIMESTAMP): When label was applied

#### `gml_attachments`
- **id** (UUID): Internal primary key
- **message_id** (UUID): Reference to gml_messages table
- **attachment_id** (TEXT): Gmail attachment ID (can be very long)
- **filename** (VARCHAR): Original attachment filename
- **mime_type** (VARCHAR): MIME type (e.g., application/pdf, image/png)
- **size_bytes** (BIGINT): File size in bytes
- **file_path** (TEXT): Local filesystem path where attachment is stored
- **download_status** (VARCHAR): Download status (pending, downloaded, failed)
- **downloaded_at** (TIMESTAMP): When the attachment was downloaded

### Views

#### `gml_message_summary`
A comprehensive view that joins messages with threads, labels, and attachment counts:

```sql
SELECT * FROM gml_message_summary WHERE sender = 'example@email.com';
```

## Usage Examples

### Query Recent Messages

```sql
SELECT * FROM gml_message_summary 
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC;
```

### Find Messages with Attachments

```sql
SELECT * FROM gml_message_summary 
WHERE attachment_count > 0
ORDER BY date DESC;
```

### Get Thread Information

```sql
SELECT t.*, COUNT(m.id) as message_count
FROM gml_threads t
LEFT JOIN gml_messages m ON t.thread_id = m.thread_id
GROUP BY t.thread_id
ORDER BY t.last_message_date DESC;
```

### Search by Sender

```sql
SELECT sender, COUNT(*) as message_count
FROM gml_messages
GROUP BY sender
ORDER BY message_count DESC;
```

## Maintenance

### Update Schema

The schema uses `IF NOT EXISTS` patterns, so you can safely re-run `gmail_schema.sql`:

```bash
psql -d gmail_data -f database/gmail_schema.sql
```

### Database Statistics

Check database statistics using the persistence module:

```python
from src.dl_gmail.db_persistence import get_database_stats

stats = get_database_stats()
print(f"Total messages: {stats['total_messages']}")
```

### Backup Database

```bash
pg_dump gmail_data > gmail_backup.sql
```

### Restore Database

```bash
psql gmail_data < gmail_backup.sql
```

## Performance

### Indexes

The schema includes indexes on frequently queried fields:
- `message_id`, `thread_id`, `sender`, `date` on gml_messages table
- `label_name` on gml_labels table
- Composite indexes for relationships

### Query Optimization

For large datasets, consider:
- Partitioning gml_messages table by date
- Archiving old messages
- Regular VACUUM and ANALYZE operations

## Troubleshooting

### Connection Issues

1. Check `.env` file configuration
2. Verify PostgreSQL is running
3. Test connection: `python -c "from src.dl_gmail.db_utils import test_database_connection; print(test_database_connection())"`

### Permission Issues

Ensure the database user has appropriate permissions:

```sql
GRANT ALL PRIVILEGES ON DATABASE gmail_data TO gmail_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gmail_user;
```

### Schema Issues

If you encounter schema conflicts:
1. Check existing tables: `\dt` in psql
2. Drop and recreate if needed (backup first!)
3. Re-run initialization script

## Future Enhancements

The schema is designed for extensibility:
- JSONB columns for additional metadata
- Version tracking for schema migrations
- Support for attachment file storage
- Full-text search capabilities
- Email content indexing

## Support

For issues with the database integration:
1. Check the logs in `logs/dl_gmail.log`
2. Verify database configuration
3. Test individual components using the provided test scripts
