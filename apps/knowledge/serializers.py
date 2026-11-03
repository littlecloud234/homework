from pathlib import Path

from rest_framework import serializers

from .models import Document, DocumentChunk, IngestionJob

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_RAW_TEXT_CHARS = 5_000_000


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "course",
            "title",
            "source_type",
            "version",
            "status",
            "file",
            "raw_text",
            "checksum",
            "effective_from",
            "effective_to",
            "metadata",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "status",
            "checksum",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        )

    def get_uploaded_by_name(self, obj) -> str:
        if not obj.uploaded_by:
            return ""
        return obj.uploaded_by.display_name or obj.uploaded_by.username

    def validate_file(self, value):
        if not value:
            return value
        suffix = Path(value.name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))} 文件。"
            )
        if value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("单个文件不能超过 50MB。")
        return value

    def validate_raw_text(self, value):
        if len(value) > MAX_RAW_TEXT_CHARS:
            raise serializers.ValidationError("直接录入文本不能超过 500 万字符。")
        return value

    def validate(self, attrs):
        if (
            self.instance
            and "course" in attrs
            and attrs["course"].pk != self.instance.course_id
        ):
            raise serializers.ValidationError("文档创建后不能更换课程，请新建文档。")

        file = attrs.get("file") or getattr(self.instance, "file", None)
        raw_text = attrs.get("raw_text")
        if raw_text is None:
            raw_text = getattr(self.instance, "raw_text", "")
        if not file and not (raw_text or "").strip():
            raise serializers.ValidationError("请上传文件或填写直接录入文本。")
        return attrs


class DocumentChunkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = DocumentChunk
        fields = (
            "id",
            "document",
            "document_title",
            "seq",
            "heading",
            "content",
            "char_count",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class IngestionJobSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = IngestionJob
        fields = (
            "id",
            "document",
            "document_title",
            "status",
            "message",
            "chunk_count",
            "started_at",
            "finished_at",
            "created_at",
        )
        read_only_fields = fields
