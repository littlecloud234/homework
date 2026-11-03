"""文档清洗、分块、向量化与入库。"""
import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.qa.services.embeddings import embed_texts

from ..models import Document, DocumentChunk, IngestionJob
from .extractors import extract_text

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s+.+"
    r"|第[一二三四五六七八九十百零〇\d]+[章节讲课].*"
    r"|[一二三四五六七八九十]+、.*"
    r"|\d+(?:\.\d+)*\s+\S.*"
    r")$"
)


@dataclass(frozen=True)
class TextChunk:
    content: str
    heading: str = ""


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int | None = None, overlap: int | None = None) -> list[TextChunk]:
    """按标题/段落分块；超长段落使用滑动窗口并保留重叠。"""
    max_chars = max_chars or settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP if overlap is None else overlap
    overlap = max(0, min(overlap, max_chars // 2))

    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[TextChunk] = []
    buffer: list[str] = []
    buffer_len = 0
    heading = ""

    def flush():
        nonlocal buffer, buffer_len
        if not buffer:
            return
        content = "\n\n".join(buffer).strip()
        if content:
            chunks.append(TextChunk(content=content, heading=heading))
        buffer = []
        buffer_len = 0

    for paragraph in paragraphs:
        first_line = paragraph.splitlines()[0].strip()
        if len(first_line) <= 80 and HEADING_RE.match(first_line):
            flush()
            heading = first_line[:255]

        if len(paragraph) <= max_chars:
            if buffer and buffer_len + len(paragraph) + 2 > max_chars:
                flush()
            buffer.append(paragraph)
            buffer_len += len(paragraph) + 2
            continue

        flush()
        start = 0
        while start < len(paragraph):
            end = min(start + max_chars, len(paragraph))
            piece = paragraph[start:end].strip()
            if piece:
                chunks.append(TextChunk(content=piece, heading=heading))
            if end >= len(paragraph):
                break
            start = max(end - overlap, start + 1)

    flush()
    return chunks


def ingest_document(document_id: int, force: bool = False) -> IngestionJob:
    """解析并重建文档的全部片段。返回本次任务记录。"""
    document = Document.objects.select_related("course").get(pk=document_id)
    current_checksum = document.compute_checksum()

    if (
        not force
        and document.status == Document.Status.READY
        and document.checksum
        and document.checksum == current_checksum
    ):
        now = timezone.now()
        return IngestionJob.objects.create(
            document=document,
            status=IngestionJob.Status.SUCCEEDED,
            message="文档内容未变化，已跳过重新解析；使用 --force 可强制重建。",
            chunk_count=document.chunks.count(),
            started_at=now,
            finished_at=now,
        )

    if document.status == Document.Status.PROCESSING and not force:
        raise RuntimeError("文档正在解析中，请稍后重试；若任务已卡死可使用 --force。")

    document.status = Document.Status.PROCESSING
    document.checksum = current_checksum
    document.save(update_fields=["status", "checksum", "updated_at"])

    job = IngestionJob.objects.create(
        document=document,
        status=IngestionJob.Status.RUNNING,
        started_at=timezone.now(),
    )

    try:
        text = extract_text(document)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("分块结果为空，文档可能没有有效文本。")

        vectors = embed_texts([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("向量数量与文本块数量不一致。")

        objects = [
            DocumentChunk(
                document=document,
                course=document.course,
                seq=index,
                heading=chunk.heading,
                content=chunk.content,
                char_count=len(chunk.content),
                embedding=vector,
                metadata={"source_version": document.version},
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1)
        ]

        with transaction.atomic():
            DocumentChunk.objects.filter(document=document).delete()
            DocumentChunk.objects.bulk_create(objects, batch_size=100)

        document.status = Document.Status.READY
        document.save(update_fields=["status", "updated_at"])

        job.status = IngestionJob.Status.SUCCEEDED
        job.chunk_count = len(objects)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "chunk_count", "finished_at"])
        logger.info("文档解析完成 document_id=%s chunks=%s", document_id, len(objects))
        return job

    except Exception as exc:
        document.status = Document.Status.FAILED
        document.save(update_fields=["status", "updated_at"])
        job.status = IngestionJob.Status.FAILED
        job.message = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "message", "finished_at"])
        logger.exception("文档解析失败 document_id=%s", document_id)
        raise
