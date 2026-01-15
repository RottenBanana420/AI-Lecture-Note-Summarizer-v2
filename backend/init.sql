-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- Verify extension installation
SELECT *
FROM pg_extension
WHERE extname = 'vector';