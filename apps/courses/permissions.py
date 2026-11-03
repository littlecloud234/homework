from rest_framework.permissions import BasePermission

from .selectors import user_can_access_course


class IsCourseMember(BasePermission):
    """对象级权限：用户必须与课程存在授课或选课关系。"""

    message = "您没有访问该课程的权限。"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return user_can_access_course(request.user, obj)
