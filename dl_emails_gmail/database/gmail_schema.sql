-- Gmail Data Database Schema
-- PostgreSQL DDL script for storing Gmail message data
-- 
-- This script creates the necessary tables for storing Gmail messages, threads,
-- labels, and attachments. All CREATE statements use IF NOT EXISTS to allow
-- safe re-execution without errors.
--
-- Tables created (with gml_ prefix for multi-app database organization):
-- - gml_threads: Email conversation threads
-- - gml_messages: Core email message data
-- - gml_labels: Gmail label definitions
-- - gml_message_labels: Many-to-many relationship between messages and labels
-- - gml_attachments: Attachment metadata with file paths
--
-- Usage:
--   psql -d your_database -f gmail_schema.sql
--   OR
--   python database/init_gmail_schema.py

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create threads table
-- Stores email conversation threads/conversations
CREATE TABLE IF NOT EXISTS gml_threads (
    thread_id VARCHAR(255) PRIMARY KEY,
    subject VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    last_message_date TIMESTAMP WITH TIME ZONE,
    -- JSONB for future extensibility (participants, thread metadata, etc.)
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create comments for threads table
COMMENT ON TABLE gml_threads IS 'Email conversation threads from Gmail';
COMMENT ON COLUMN gml_threads.thread_id IS 'Gmail thread ID (primary key)';
COMMENT ON COLUMN gml_threads.subject IS 'Thread subject (from most recent message)';
COMMENT ON COLUMN gml_threads.message_count IS 'Total number of messages in this thread';
COMMENT ON COLUMN gml_threads.last_message_date IS 'Date of the most recent message in thread';
COMMENT ON COLUMN gml_threads.metadata IS 'Additional thread metadata (JSONB for extensibility)';

-- Create labels table
-- Stores Gmail label definitions
CREATE TABLE IF NOT EXISTS gml_labels (
    label_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    label_type VARCHAR(50) DEFAULT 'user', -- user, system, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- JSONB for future extensibility (color, visibility settings, etc.)
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create comments for labels table
COMMENT ON TABLE gml_labels IS 'Gmail label definitions';
COMMENT ON COLUMN gml_labels.label_id IS 'Gmail label ID (primary key)';
COMMENT ON COLUMN gml_labels.name IS 'Human-readable label name';
COMMENT ON COLUMN gml_labels.label_type IS 'Type of label (user, system, etc.)';
COMMENT ON COLUMN gml_labels.metadata IS 'Additional label metadata (JSONB for extensibility)';

-- Create messages table
-- Core email message data
CREATE TABLE IF NOT EXISTS gml_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(255) NOT NULL UNIQUE, -- Gmail message ID
    thread_id VARCHAR(255) NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT,
    subject VARCHAR(1000),
    date TIMESTAMP WITH TIME ZONE,
    internal_date TIMESTAMP WITH TIME ZONE,
    snippet TEXT,
    body_text TEXT,
    size_estimate INTEGER,
    processed_successfully BOOLEAN DEFAULT FALSE,
    label_applied BOOLEAN DEFAULT FALSE,
    saved_to_db BOOLEAN DEFAULT FALSE,
    processing_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- JSONB for future extensibility (headers, additional metadata, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Foreign key constraints
    CONSTRAINT fk_gml_messages_thread_id FOREIGN KEY (thread_id) 
        REFERENCES gml_threads(thread_id) ON DELETE CASCADE
);

-- Create comments for messages table
COMMENT ON TABLE gml_messages IS 'Core Gmail message data';
COMMENT ON COLUMN gml_messages.id IS 'Internal UUID primary key';
COMMENT ON COLUMN gml_messages.message_id IS 'Gmail message ID (unique)';
COMMENT ON COLUMN gml_messages.thread_id IS 'Reference to threads table';
COMMENT ON COLUMN gml_messages.sender IS 'Email sender address';
COMMENT ON COLUMN gml_messages.recipient IS 'Email recipient address';
COMMENT ON COLUMN gml_messages.date IS 'Email date from headers';
COMMENT ON COLUMN gml_messages.internal_date IS 'Gmail internal date';
COMMENT ON COLUMN gml_messages.body_text IS 'Plain text email body';
COMMENT ON COLUMN gml_messages.processed_successfully IS 'Whether message was processed without errors';
COMMENT ON COLUMN gml_messages.label_applied IS 'Whether Gmail labels were updated';
COMMENT ON COLUMN gml_messages.saved_to_db IS 'Whether message was saved to database';
COMMENT ON COLUMN gml_messages.metadata IS 'Additional message metadata (JSONB for extensibility)';

-- Create message_labels table
-- Many-to-many relationship between messages and labels
CREATE TABLE IF NOT EXISTS gml_message_labels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL,
    label_id VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_gml_message_labels_message_id FOREIGN KEY (message_id) 
        REFERENCES gml_messages(id) ON DELETE CASCADE,
    CONSTRAINT fk_gml_message_labels_label_id FOREIGN KEY (label_id) 
        REFERENCES gml_labels(label_id) ON DELETE CASCADE,
    
    -- Ensure unique message-label combinations
    CONSTRAINT uk_gml_message_labels_unique UNIQUE (message_id, label_id)
);

-- Create comments for message_labels table
COMMENT ON TABLE gml_message_labels IS 'Many-to-many relationship between messages and labels';
COMMENT ON COLUMN gml_message_labels.message_id IS 'Reference to messages table';
COMMENT ON COLUMN gml_message_labels.label_id IS 'Reference to labels table';
COMMENT ON COLUMN gml_message_labels.applied_at IS 'When the label was applied to the message';

-- Create attachments table
-- Attachment metadata with file paths
CREATE TABLE IF NOT EXISTS gml_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL,
    attachment_id TEXT NOT NULL, -- Gmail attachment ID (can be very long)
    filename VARCHAR(500),
    mime_type VARCHAR(255),
    size_bytes BIGINT,
    file_path TEXT, -- Local file system path where attachment is stored
    download_status VARCHAR(50) DEFAULT 'pending', -- pending, downloaded, failed
    downloaded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_gml_attachments_message_id FOREIGN KEY (message_id) 
        REFERENCES gml_messages(id) ON DELETE CASCADE,
    
    -- Ensure unique message-attachment combinations
    CONSTRAINT uk_gml_attachments_unique UNIQUE (message_id, attachment_id)
);

-- Create comments for attachments table
COMMENT ON TABLE gml_attachments IS 'Email attachment metadata and file paths';
COMMENT ON COLUMN gml_attachments.message_id IS 'Reference to messages table';
COMMENT ON COLUMN gml_attachments.attachment_id IS 'Gmail attachment ID';
COMMENT ON COLUMN gml_attachments.filename IS 'Original attachment filename';
COMMENT ON COLUMN gml_attachments.mime_type IS 'MIME type of the attachment';
COMMENT ON COLUMN gml_attachments.size_bytes IS 'Attachment size in bytes';
COMMENT ON COLUMN gml_attachments.file_path IS 'Local file system path where attachment is stored';
COMMENT ON COLUMN gml_attachments.download_status IS 'Status of attachment download (pending, downloaded, failed)';

-- Create indexes for performance
-- Index on frequently queried fields

-- Messages table indexes
CREATE INDEX IF NOT EXISTS idx_gml_messages_message_id ON gml_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_gml_messages_thread_id ON gml_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_gml_messages_sender ON gml_messages(sender);
CREATE INDEX IF NOT EXISTS idx_gml_messages_date ON gml_messages(date);
CREATE INDEX IF NOT EXISTS idx_gml_messages_internal_date ON gml_messages(internal_date);
CREATE INDEX IF NOT EXISTS idx_gml_messages_processed_successfully ON gml_messages(processed_successfully);
CREATE INDEX IF NOT EXISTS idx_gml_messages_saved_to_db ON gml_messages(saved_to_db);

-- Threads table indexes
CREATE INDEX IF NOT EXISTS idx_gml_threads_subject ON gml_threads(subject);
CREATE INDEX IF NOT EXISTS idx_gml_threads_last_message_date ON gml_threads(last_message_date);

-- Labels table indexes
CREATE INDEX IF NOT EXISTS idx_gml_labels_name ON gml_labels(name);
CREATE INDEX IF NOT EXISTS idx_gml_labels_type ON gml_labels(label_type);

-- Message_labels table indexes
CREATE INDEX IF NOT EXISTS idx_gml_message_labels_message_id ON gml_message_labels(message_id);
CREATE INDEX IF NOT EXISTS idx_gml_message_labels_label_id ON gml_message_labels(label_id);

-- Attachments table indexes
CREATE INDEX IF NOT EXISTS idx_gml_attachments_message_id ON gml_attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_gml_attachments_attachment_id ON gml_attachments(attachment_id);
CREATE INDEX IF NOT EXISTS idx_gml_attachments_download_status ON gml_attachments(download_status);

-- Create triggers for updated_at timestamps
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to relevant tables
DROP TRIGGER IF EXISTS update_gml_threads_updated_at ON gml_threads;
CREATE TRIGGER update_gml_threads_updated_at 
    BEFORE UPDATE ON gml_threads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_gml_messages_updated_at ON gml_messages;
CREATE TRIGGER update_gml_messages_updated_at 
    BEFORE UPDATE ON gml_messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert common system labels
-- These are standard Gmail labels that we want to track
INSERT INTO gml_labels (label_id, name, label_type) VALUES 
    ('INBOX', 'INBOX', 'system'),
    ('SENT', 'SENT', 'system'),
    ('DRAFT', 'DRAFT', 'system'),
    ('SPAM', 'SPAM', 'system'),
    ('TRASH', 'TRASH', 'system'),
    ('UNREAD', 'UNREAD', 'system'),
    ('STARRED', 'STARRED', 'system'),
    ('IMPORTANT', 'IMPORTANT', 'system')
ON CONFLICT (label_id) DO NOTHING;

-- Create view for message summary with thread and label information
CREATE OR REPLACE VIEW gml_message_summary AS
SELECT 
    m.id,
    m.message_id,
    m.thread_id,
    t.subject as thread_subject,
    m.sender,
    m.recipient,
    m.subject,
    m.date,
    m.snippet,
    m.processed_successfully,
    m.label_applied,
    m.saved_to_db,
    m.created_at,
    -- Aggregate labels into array
    COALESCE(
        array_agg(DISTINCT l.name) FILTER (WHERE l.name IS NOT NULL), 
        ARRAY[]::text[]
    ) as labels,
    -- Count attachments
    COALESCE(att_count.attachment_count, 0) as attachment_count
FROM gml_messages m
LEFT JOIN gml_threads t ON m.thread_id = t.thread_id
LEFT JOIN gml_message_labels ml ON m.id = ml.message_id
LEFT JOIN gml_labels l ON ml.label_id = l.label_id
LEFT JOIN (
    SELECT message_id, COUNT(*) as attachment_count 
    FROM gml_attachments 
    GROUP BY message_id
) att_count ON m.id = att_count.message_id
GROUP BY m.id, m.message_id, m.thread_id, t.subject, m.sender, m.recipient, 
         m.subject, m.date, m.snippet, m.processed_successfully, m.label_applied, 
         m.saved_to_db, m.created_at, att_count.attachment_count;

-- Add comment to the view
COMMENT ON VIEW gml_message_summary IS 'Summary view of messages with thread and label information';

-- Grant permissions (adjust as needed for your setup)
-- These are commented out - uncomment and modify as needed for your environment
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gmail_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gmail_user;
-- GRANT SELECT ON gml_message_summary TO gmail_user;

-- Schema version tracking
-- Create a table to track schema versions for future migrations
CREATE TABLE IF NOT EXISTS gml_schema_versions (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Record this schema version
INSERT INTO gml_schema_versions (version, description) VALUES 
    ('1.0', 'Initial schema with gml_threads, gml_messages, gml_labels, gml_message_labels, and gml_attachments tables')
ON CONFLICT (version) DO NOTHING;

-- Display completion message
DO $$
BEGIN
    RAISE NOTICE 'Gmail database schema created successfully!';
    RAISE NOTICE 'Tables created: gml_threads, gml_messages, gml_labels, gml_message_labels, gml_attachments';
    RAISE NOTICE 'View created: gml_message_summary';
    RAISE NOTICE 'Schema version: 1.0';
END $$;
