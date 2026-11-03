from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.courses.models import Course, Enrollment


class Command(BaseCommand):
    help = "创建演示教师、学生、课程与选课关系（仅用于开发环境）"

    def handle(self, *args, **options):
        teacher, teacher_created = User.objects.get_or_create(
            username="demo_teacher",
            defaults={
                "role": User.Role.TEACHER,
                "display_name": "演示教师",
                "department": "计算机学院",
            },
        )
        if teacher_created:
            teacher.set_password("teacher123")
            teacher.save()

        student, student_created = User.objects.get_or_create(
            username="demo_student",
            defaults={
                "role": User.Role.STUDENT,
                "display_name": "演示学生",
                "department": "计算机学院",
            },
        )
        if student_created:
            student.set_password("student123")
            student.save()

        admin, admin_created = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "role": User.Role.ADMIN,
                "display_name": "演示管理员",
                "department": "信息中心",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if admin_created:
            admin.set_password("admin123")
            admin.save()

        course, _ = Course.objects.get_or_create(
            code="CS101",
            defaults={
                "title": "程序设计基础",
                "description": "演示课程：用于验证课程知识库问答闭环。",
                "teacher": teacher,
            },
        )
        if course.teacher_id != teacher.id:
            course.teacher = teacher
            course.save(update_fields=["teacher", "updated_at"])

        Enrollment.objects.get_or_create(course=course, student=student)

        self.stdout.write(self.style.SUCCESS("演示数据已就绪。"))
        self.stdout.write(f"教师：demo_teacher / teacher123（{course.code}，可通过 API 维护知识库）")
        self.stdout.write("学生：demo_student / student123")
        self.stdout.write("管理员：demo_admin / admin123（可登录 /admin/）")
        self.stdout.write("下一步：进入 /admin/ 上传课程资料，或通过文档 API 创建后执行 make ingest COURSE=CS101")
