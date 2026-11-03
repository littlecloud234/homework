-- 在业务表创建之前启用扩展。
-- pgvector 镜像已自带 vector；pg_trgm 用于二期关键词检索。
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
