"""文本提取：支持文本型 PDF、DOCX、PPTX、TXT、MD。

扫描件 PDF 需要 OCR，不在 MVP 范围内；解析为空时会明确报错。
"""
from pathlib import Path

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


def extract_text(document) -> str:
    """原始文件优先于直接录入文本，避免替换文件后仍使用旧 raw_text。"""
    if not document.file and document.raw_text and document.raw_text.strip():
        return document.raw_text

    if not document.file:
        raise ValueError("文档既没有原始文件，也没有直接录入文本。")

    suffix = Path(document.file.name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"暂不支持的文件类型：{suffix or '未知'}")

    with document.file.open("rb") as fh:
        if suffix == ".pdf":
            text = _extract_pdf(fh)
        elif suffix == ".docx":
            text = _extract_docx(fh)
        elif suffix == ".pptx":
            text = _extract_pptx(fh)
        else:
            text = _extract_plain_text(fh)

    if not text.strip():
        raise ValueError("未能从文档中提取到文本；若为扫描件，请先做 OCR。")
    return text


def _extract_pdf(fh) -> str:
    reader = PdfReader(fh)
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"[第{index}页]\n{text}")
    return "\n\n".join(pages)


def _extract_docx(fh) -> str:
    document = DocxDocument(fh)
    parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def _extract_pptx(fh) -> str:
    presentation = Presentation(fh)
    parts = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = shape.text_frame.text.strip()
                if text:
                    texts.append(text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):
                        texts.append(" | ".join(cells))
        if texts:
            parts.append(f"[第{index}页]\n" + "\n".join(texts))
    return "\n\n".join(parts)


def _extract_plain_text(fh) -> str:
    data = fh.read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
