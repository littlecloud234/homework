from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .selectors import accessible_courses
from .serializers import CourseSerializer


class CourseViewSet(ReadOnlyModelViewSet):
    """当前用户可见的课程列表 / 详情。"""

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return accessible_courses(self.request.user).select_related("teacher")
