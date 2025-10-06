-- DDL Script: Create Diary and Transcription Tables
-- Created: 2024-01-03
-- Database: PostgreSQL
-- 
-- This script creates normalized tables for diary entries and transcription metadata
-- Includes diary, source_file, transcription_run, and transcription_usage tables
-- Safe to run multiple times during development

-- Create diary table (only if it doesn't exist)
CREATE TABLE IF NOT EXISTS gdr_diary (
    -- Primary key field
    id SERIAL PRIMARY KEY,
    uuid UUID,
    
    -- Timestamp field for when the entry was created
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional useful diary fields
    title VARCHAR(255),
    text TEXT NOT NULL,
    revised_text TEXT,
    mood VARCHAR(50),
    tags TEXT[],
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT gdr_diary_text_not_empty CHECK (LENGTH(TRIM(text)) > 0)
);

-- Add new columns to existing table (for development updates)
-- ALTER TABLE gdr_diary ADD COLUMN IF NOT EXISTS uuid UUID;
-- ALTER TABLE gdr_diary ADD COLUMN IF NOT EXISTS revised_text TEXT;

-- Create indexes for better performance (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_gdr_diary_created_at ON gdr_diary(created_at);
CREATE INDEX IF NOT EXISTS idx_gdr_diary_updated_at ON gdr_diary(updated_at);
CREATE INDEX IF NOT EXISTS idx_gdr_diary_mood ON gdr_diary(mood);

-- Create trigger to automatically update the updated_at field
CREATE OR REPLACE FUNCTION update_gdr_diary_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_gdr_diary_updated_at ON gdr_diary;
CREATE TRIGGER trigger_update_gdr_diary_updated_at
    BEFORE UPDATE ON gdr_diary
    FOR EACH ROW
    EXECUTE FUNCTION update_gdr_diary_updated_at();

-- Add comments for documentation
COMMENT ON TABLE gdr_diary IS 'Table to store diary entries with timestamps and metadata';
COMMENT ON COLUMN gdr_diary.id IS 'Primary key - auto-incrementing integer';
COMMENT ON COLUMN gdr_diary.uuid IS 'Unique identifier (UUID) for the diary entry - populated by external script';
COMMENT ON COLUMN gdr_diary.created_at IS 'Timestamp when the diary entry was first created';
COMMENT ON COLUMN gdr_diary.title IS 'Title of the diary entry (required)';
COMMENT ON COLUMN gdr_diary.text IS 'Main content/body of the diary entry';
COMMENT ON COLUMN gdr_diary.revised_text IS 'Revised or edited version of the diary content';
COMMENT ON COLUMN gdr_diary.mood IS 'Optional mood indicator for the entry';
COMMENT ON COLUMN gdr_diary.tags IS 'Array of tags associated with the entry';
COMMENT ON COLUMN gdr_diary.updated_at IS 'Timestamp when the diary entry was last modified';

-- Insert sample data (optional - remove if not needed)
-- Only insert if no data exists to avoid duplicates
--     INSERT INTO gdr_diary (title, text, mood, tags) 
-- SELECT 'First Entry', 'This is my first diary entry!', 'excited', ARRAY['first', 'milestone']
-- WHERE NOT EXISTS (SELECT 1 FROM gdr_diary WHERE title = 'First Entry');

--     INSERT INTO gdr_diary (title, text, mood, tags) 
-- SELECT 'Daily Reflection', 'Today was a productive day. I learned something new.', 'content', ARRAY['reflection', 'learning']
-- WHERE NOT EXISTS (SELECT 1 FROM gdr_diary WHERE title = 'Daily Reflection');

-- Create source_file table for tracking audio file sources
CREATE TABLE IF NOT EXISTS gdr_source_file (
    -- Primary key field
    id SERIAL PRIMARY KEY,
    
    -- File path from transcription metadata
    path TEXT NOT NULL UNIQUE,
    
    -- Google Drive file ID (derived from directory name)
    file_id VARCHAR(64) NULL,
    
    -- Optional file hash for future deduplication
    file_hash TEXT NULL,
    
    -- Timestamp when file was first recorded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create transcription_run table for storing transcription metadata
CREATE TABLE IF NOT EXISTS gdr_transcription_run (
    -- Primary key field
    id SERIAL PRIMARY KEY,
    
    -- Foreign key to diary entry (1:1 relationship)
    diary_id INT NOT NULL UNIQUE REFERENCES gdr_diary(id) ON DELETE CASCADE,
    
    -- Unique run identifier for idempotency/auditing
    run_uuid UUID UNIQUE,
    
    -- Foreign key to source file
    source_file_id INT NULL REFERENCES gdr_source_file(id) ON DELETE SET NULL,
    
    -- Model information
    model TEXT NULL,
    detect_model TEXT NULL,
    
    -- Language settings
    forced_language BOOLEAN NULL,
    language_routing_enabled BOOLEAN NULL,
    routed_language TEXT NULL,
    
    -- Processing flags
    probe_seconds DOUBLE PRECISION NULL,
    ffmpeg_used BOOLEAN NULL,
    
    -- Quick flag for logprobs presence
    logprobs_present BOOLEAN NULL,
    
    -- Full raw API response for auditing/debugging
    response_json JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create transcription_usage table for token usage tracking
CREATE TABLE IF NOT EXISTS gdr_transcription_usage (
    -- Primary key field
    id SERIAL PRIMARY KEY,
    
    -- Foreign key to transcription run (1:1 relationship)
    run_id INT NOT NULL UNIQUE REFERENCES gdr_transcription_run(id) ON DELETE CASCADE,
    
    -- Usage type (e.g., "tokens")
    type TEXT NULL,
    
    -- Token counts
    input_tokens INT NULL,
    output_tokens INT NULL,
    total_tokens INT NULL,
    
    -- Token type breakdown
    audio_tokens INT NULL,
    text_tokens INT NULL,
    
    -- Timestamp when usage was recorded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance (only if they don't exist)
-- Diary indexes (existing)
CREATE INDEX IF NOT EXISTS idx_gdr_diary_created_at ON gdr_diary(created_at);
CREATE INDEX IF NOT EXISTS idx_gdr_diary_updated_at ON gdr_diary(updated_at);
CREATE INDEX IF NOT EXISTS idx_gdr_diary_mood ON gdr_diary(mood);

-- Source file indexes
CREATE INDEX IF NOT EXISTS idx_gdr_source_file_path ON gdr_source_file(path);
CREATE INDEX IF NOT EXISTS idx_gdr_source_file_file_id ON gdr_source_file(file_id);

-- Transcription run indexes
CREATE INDEX IF NOT EXISTS idx_gdr_transcription_run_diary_id ON gdr_transcription_run(diary_id);
-- Unique index on run_uuid is implied by the UNIQUE constraint
CREATE INDEX IF NOT EXISTS idx_gdr_transcription_run_source_file_id ON gdr_transcription_run(source_file_id);
CREATE INDEX IF NOT EXISTS idx_gdr_transcription_run_created_at ON gdr_transcription_run(created_at);

-- Transcription usage indexes
CREATE INDEX IF NOT EXISTS idx_gdr_transcription_usage_run_id ON gdr_transcription_usage(run_id);

-- Create trigger to automatically update the updated_at field for transcription_run
CREATE OR REPLACE FUNCTION update_gdr_transcription_run_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_gdr_transcription_run_updated_at ON gdr_transcription_run;
CREATE TRIGGER trigger_update_gdr_transcription_run_updated_at
    BEFORE UPDATE ON gdr_transcription_run
    FOR EACH ROW
    EXECUTE FUNCTION update_gdr_transcription_run_updated_at();

-- Add comments for documentation
-- Diary table comments (existing)
COMMENT ON TABLE gdr_diary IS 'Table to store diary entries with timestamps and metadata';
COMMENT ON COLUMN gdr_diary.id IS 'Primary key - auto-incrementing integer';
COMMENT ON COLUMN gdr_diary.uuid IS 'Unique identifier (UUID) for the diary entry - populated by external script';
COMMENT ON COLUMN gdr_diary.created_at IS 'Timestamp when the diary entry was first created';
COMMENT ON COLUMN gdr_diary.title IS 'Title of the diary entry (optional)';
COMMENT ON COLUMN gdr_diary.text IS 'Main content/body of the diary entry';
COMMENT ON COLUMN gdr_diary.revised_text IS 'Revised or edited version of the diary content';
COMMENT ON COLUMN gdr_diary.mood IS 'Optional mood indicator for the entry';
COMMENT ON COLUMN gdr_diary.tags IS 'Array of tags associated with the entry';
COMMENT ON COLUMN gdr_diary.updated_at IS 'Timestamp when the diary entry was last modified';

-- Source file table comments
COMMENT ON TABLE gdr_source_file IS 'Table to store source audio file information for transcription tracking';
COMMENT ON COLUMN gdr_source_file.id IS 'Primary key - auto-incrementing integer';
COMMENT ON COLUMN gdr_source_file.path IS 'Unique file path from transcription metadata';
COMMENT ON COLUMN gdr_source_file.file_hash IS 'Optional file hash for future deduplication';
COMMENT ON COLUMN gdr_source_file.created_at IS 'Timestamp when file was first recorded';

-- Transcription run table comments
COMMENT ON TABLE gdr_transcription_run IS 'Table to store transcription run metadata with 1:1 relationship to diary entries';
COMMENT ON COLUMN gdr_transcription_run.id IS 'Primary key - auto-incrementing integer';
COMMENT ON COLUMN gdr_transcription_run.diary_id IS 'Foreign key to diary entry (unique, enforces 1:1 relationship)';
COMMENT ON COLUMN gdr_transcription_run.run_uuid IS 'Unique identifier for the transcription run (idempotency/audit)';
COMMENT ON COLUMN gdr_transcription_run.source_file_id IS 'Foreign key to source file (optional)';
COMMENT ON COLUMN gdr_transcription_run.model IS 'AI model used for transcription';
COMMENT ON COLUMN gdr_transcription_run.detect_model IS 'AI model used for language detection';
COMMENT ON COLUMN gdr_transcription_run.forced_language IS 'Whether language was forced in transcription';
COMMENT ON COLUMN gdr_transcription_run.language_routing_enabled IS 'Whether language routing was enabled';
COMMENT ON COLUMN gdr_transcription_run.routed_language IS 'Language that was routed to';
COMMENT ON COLUMN gdr_transcription_run.probe_seconds IS 'Number of seconds probed from audio file';
COMMENT ON COLUMN gdr_transcription_run.ffmpeg_used IS 'Whether ffmpeg was used in processing';
COMMENT ON COLUMN gdr_transcription_run.logprobs_present IS 'Quick flag indicating if logprobs are present in response';
COMMENT ON COLUMN gdr_transcription_run.response_json IS 'Full raw API response stored as JSONB for auditing/debugging';
COMMENT ON COLUMN gdr_transcription_run.created_at IS 'Timestamp when transcription run was created';
COMMENT ON COLUMN gdr_transcription_run.updated_at IS 'Timestamp when transcription run was last modified';

-- Transcription usage table comments
COMMENT ON TABLE gdr_transcription_usage IS 'Table to store token usage information for transcription runs';
COMMENT ON COLUMN gdr_transcription_usage.id IS 'Primary key - auto-incrementing integer';
COMMENT ON COLUMN gdr_transcription_usage.run_id IS 'Foreign key to transcription run (unique, enforces 1:1 relationship)';
COMMENT ON COLUMN gdr_transcription_usage.type IS 'Usage type (e.g., "tokens")';
COMMENT ON COLUMN gdr_transcription_usage.input_tokens IS 'Number of input tokens consumed';
COMMENT ON COLUMN gdr_transcription_usage.output_tokens IS 'Number of output tokens generated';
COMMENT ON COLUMN gdr_transcription_usage.total_tokens IS 'Total tokens consumed';
COMMENT ON COLUMN gdr_transcription_usage.audio_tokens IS 'Number of audio tokens consumed';
COMMENT ON COLUMN gdr_transcription_usage.text_tokens IS 'Number of text tokens consumed';
COMMENT ON COLUMN gdr_transcription_usage.created_at IS 'Timestamp when usage was recorded';

-- Show sample data
-- SELECT * FROM gdr_diary ORDER BY created_at DESC;

-- Schema version tracking
-- Create a table to track schema versions for future migrations
CREATE TABLE IF NOT EXISTS gdr_schema_versions (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Record this schema version
INSERT INTO gdr_schema_versions (version, description) VALUES 
    ('1.0', 'Initial schema with gdr_diary, gdr_source_file, gdr_transcription_run, and gdr_transcription_usage tables')
ON CONFLICT (version) DO NOTHING;

-- Display completion message
DO $$
BEGIN
    RAISE NOTICE 'GDrive database schema created successfully!';
    RAISE NOTICE 'Tables created: gdr_diary, gdr_source_file, gdr_transcription_run, gdr_transcription_usage';
    RAISE NOTICE 'Schema version: 1.0';
END $$;
