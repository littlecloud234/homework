import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def ingest_document_task(self, document_id: int, force: bool = False):
    """异步解析文档；失败会重试，最终状态记录在 IngestionJob。"""
    from .services.ingestion import ingest_document

    try:
        job = ingest_document(document_id, force=force)
        return {
            "job_id": job.id,
            "status": job.status,
            "chunks": job.chunk_count,
        }
    except Exception as exc:  # noqa: BLE001 - 任务边界统一记录并重试
        logger.exception("文档解析失败 document_id=%s", document_id)
        raise self.retry(exc=exc)
