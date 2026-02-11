-- Migration: Add storage fields to uploads table
-- Date: 2026-01-10
-- Description: Add fields for tracking storage type, key, and URL

-- Add storage_type column
ALTER TABLE uploads
ADD COLUMN storage_type VARCHAR(20) DEFAULT 'local'
COMMENT '存储类型：local或oss';

-- Add storage_key column
ALTER TABLE uploads
ADD COLUMN storage_key VARCHAR(500) DEFAULT NULL
COMMENT 'OSS key或本地路径';

-- Add file_url column
ALTER TABLE uploads
ADD COLUMN file_url TEXT DEFAULT NULL
COMMENT '文件访问URL';

-- Create index on storage_type for queries
CREATE INDEX idx_storage_type ON uploads(storage_type);

-- Verify the migration
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_DEFAULT,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM
    INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'uploads'
    AND COLUMN_NAME IN ('storage_type', 'storage_key', 'file_url');

-- Expected output should show the three new columns
