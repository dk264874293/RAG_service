-- Rollback: Remove storage fields from uploads table
-- Date: 2026-01-10
-- Description: Remove fields for tracking storage type, key, and URL

-- Drop index on storage_type
DROP INDEX IF EXISTS idx_storage_type ON uploads;

-- Remove file_url column
ALTER TABLE uploads
DROP COLUMN IF EXISTS file_url;

-- Remove storage_key column
ALTER TABLE uploads
DROP COLUMN IF EXISTS storage_key;

-- Remove storage_type column
ALTER TABLE uploads
DROP COLUMN IF EXISTS storage_type;

-- Verify the rollback
SELECT
    COLUMN_NAME,
    DATA_TYPE
FROM
    INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'uploads'
    AND COLUMN_NAME IN ('storage_type', 'storage_key', 'file_url');

-- Expected output should be empty (no matching columns)
