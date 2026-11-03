import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.courses.selectors import accessible_courses, user_can_manage_course

from .models import Document, IngestionJob
from .serializers import DocumentSerializer, IngestionJobSerializer
from .tasks import ingest_document_task

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """课程资料管理。学生可读，教师/管理员可写与触发解析。"""

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Document.objects.filter(
                course__in=accessible_courses(self.request.user)
            )
            .select_related("course", "uploaded_by")
        )
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def _ensure_manager(self, course):
        if not user_can_manage_course(self.request.user, course):
            raise PermissionDenied("只有课程教师或管理员可以维护知识库。")

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        self._ensure_manager(course)
        document = serializer.save(
            uploaded_by=self.request.user,
            status=Document.Status.UPLOADED,
        )
        document.checksum = document.compute_checksum()
        document.save(update_fields=["checksum", "updated_at"])

    def perform_update(self, serializer):
        document = self.get_object()
        self._ensure_manager(document.course)
        changed = any(
            field in serializer.validated_data for field in ("file", "raw_text")
        )
        document = serializer.save()
        document.checksum = document.compute_checksum()
        if changed:
            document.status = Document.Status.UPLOADED
        document.save(update_fields=["checksum", "status", "updated_at"])

    def perform_destroy(self, instance):
        self._ensure_manager(instance.course)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="ingest")
    def ingest(self, request, pk=None):
        document = self.get_object()
        self._ensure_manager(document.course)
        if not document.file and not document.raw_text.strip():
            return Response(
                {"detail": "文档没有可解析的内容。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        force = request.query_params.get("force") in {"1", "true", "yes"}
        try:
            task = ingest_document_task.delay(document.id, force=force)
        except Exception:  # noqa: BLE001 - 队列不可用时返回可诊断的错误
            logger.exception("无法提交解析任务 document_id=%s", document.id)
            return Response(
                {"detail": "任务队列不可用，请检查 Redis / Celery Worker。"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {"detail": "解析任务已提交。", "task_id": getattr(task, "id", None)},
            status=status.HTTP_202_ACCEPTED,
        )


class IngestionJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = IngestionJob.objects.filter(
            document__course__in=accessible_courses(self.request.user)
        ).select_related("document")
        document_id = self.request.query_params.get("document")
        if document_id:
            qs = qs.filter(document_id=document_id)
        return qs
