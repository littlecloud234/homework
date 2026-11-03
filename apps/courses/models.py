from django.conf import settings
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True, verbose_name="课程代码")
    title = models.CharField(max_length=128, verbose_name="课程名称")
    description = models.TextField(blank=True, verbose_name="课程简介")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="teaching_courses",
        null=True,
        blank=True,
        verbose_name="任课教师",
    )
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "课程"
        verbose_name_plural = "课程"

    def __str__(self):
        return f"{self.code} {self.title}"


class Enrollment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="课程",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="学生",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "选课关系"
        verbose_name_plural = "选课关系"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"],
                name="uniq_course_student",
            )
        ]

    def __str__(self):
        return f"{self.student} @ {self.course.code}"
