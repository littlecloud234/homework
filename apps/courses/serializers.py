from rest_framework import serializers

from .models import Course


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("id", "code", "title", "description", "teacher_name", "is_active")
        read_only_fields = fields

    def get_teacher_name(self, obj) -> str:
        if not obj.teacher:
            return ""
        return obj.teacher.display_name or obj.teacher.username
