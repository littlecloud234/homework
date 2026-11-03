from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """教学场景用户：学生 / 教师 / 管理员。"""

    class Role(models.TextChoices):
        STUDENT = "student", "学生"
        TEACHER = "teacher", "教师"
        ADMIN = "admin", "管理员"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="角色",
    )
    display_name = models.CharField(max_length=64, blank=True, verbose_name="显示名")
    department = models.CharField(max_length=128, blank=True, verbose_name="院系")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.display_name or self.username
