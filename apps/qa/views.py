from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course
from apps.courses.permissions import IsCourseMember
from apps.courses.selectors import accessible_courses, user_can_access_course

from .models import Conversation, Feedback, Message, UnansweredQuestion
from .serializers import (
    AskSerializer,
    ConversationSerializer,
    FeedbackSerializer,
    MessageSerializer,
)
from .services.queue import record_unanswered
from .services.rag import answer_question


class ChatPageView(LoginRequiredMixin, TemplateView):
    template_name = "chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = accessible_courses(self.request.user)
        context["courses"] = courses.select_related("teacher")
        context["conversations"] = (
            Conversation.objects.filter(
                user=self.request.user,
                course__in=courses,
            )
            .select_related("course")
            .order_by("-updated_at")[:20]
        )
        return context


class AskView(APIView):
    permission_classes = [IsAuthenticated, IsCourseMember]

    def post(self, request, course_id: int):
        course = get_object_or_404(
            Course.objects.select_related("teacher"),
            pk=course_id,
            is_active=True,
        )
        self.check_object_permissions(request, course)

        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = None
        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
                course=course,
            )

        message = answer_question(
            course=course,
            user=request.user,
            question=serializer.validated_data["question"],
            conversation=conversation,
        )
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Conversation.objects.filter(
                user=self.request.user,
                course__in=accessible_courses(self.request.user),
            )
            .select_related("course")
            .prefetch_related("messages__citations")
        )
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs


class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        message = get_object_or_404(
            Message.objects.select_related("conversation"),
            pk=pk,
        )
        if message.conversation.user_id != request.user.id:
            raise PermissionDenied("只能评价自己的会话。")
        if not user_can_access_course(request.user, message.conversation.course):
            raise PermissionDenied("您没有该课程的访问权限。")
        if message.role != Message.Role.ASSISTANT:
            raise PermissionDenied("只能评价助手的回答。")

        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback, _created = Feedback.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={
                "rating": serializer.validated_data["rating"],
                "comment": serializer.validated_data.get("comment", ""),
            },
        )

        # 找到被评价回答之前的最后一条学生消息，避免把“最新问题”错配给旧回答。
        question = (
            message.conversation.messages.filter(
                role=Message.Role.USER,
                created_at__lt=message.created_at,
            )
            .order_by("-created_at")
            .values_list("content", flat=True)
            .first()
        )
        course = message.conversation.course
        if question and feedback.rating < 0:
            if not message.needs_review:
                message.needs_review = True
                message.save(update_fields=["needs_review"])
            # 拒答时 RAG 已可能写入记录，这里按课程+问题去重。
            record_unanswered(
                course=course,
                user=request.user,
                question=question,
                reason=UnansweredQuestion.Reason.USER_THUMBS_DOWN,
            )
        elif question:
            # 只关闭当前用户自己的开放待办，避免影响其他学生的记录。
            UnansweredQuestion.objects.filter(
                course=course,
                question=question,
                user=request.user,
                reason=UnansweredQuestion.Reason.USER_THUMBS_DOWN,
                status=UnansweredQuestion.Status.OPEN,
            ).update(
                status=UnansweredQuestion.Status.RESOLVED,
                resolved_at=timezone.now(),
            )

        return Response({"ok": True, "feedback_id": feedback.id})
