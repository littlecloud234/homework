-- 在知识库有一定数据量后执行；小数据量顺序扫描即可。
-- 注意：表名来自 Django 默认命名，如修改 db_table 需同步调整。
CREATE INDEX IF NOT EXISTS idx_documentchunk_embedding_hnsw
ON knowledge_documentchunk
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 课程过滤 + 文档顺序
CREATE INDEX IF NOT EXISTS idx_chunk_course_document
ON knowledge_documentchunk (course_id, document_id, seq);
