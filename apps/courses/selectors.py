from __future__ import annotations

from django.db.models import Q, QuerySet

from .models import Course


def accessible_courses(user) -> QuerySet[Course]:
    """返回用户可访问且已启用的课程：管理员全部，教师本人课程，学生已选课程。"""
    qs = Course.objects.filter(is_active=True)
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if user.is_staff or getattr(user, "role", "") == "admin":
        return qs
    return qs.filter(Q(teacher=user) | Q(enrollments__student=user)).distinct()


def user_can_access_course(user, course: Course) -> bool:
    return accessible_courses(user).filter(pk=course.pk).exists()


def user_can_manage_course(user, course: Course) -> bool:
    """课程知识库的维护权限：管理员或本课程教师。"""
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(
        user.is_staff
        or getattr(user, "role", "") == "admin"
        or course.teacher_id == user.id
    )
