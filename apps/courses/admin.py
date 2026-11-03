from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "teacher", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "title")
    autocomplete_fields = ("teacher",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "created_at")
    list_filter = ("course",)
    search_fields = ("course__code", "course__title", "student__username", "student__display_name")
    autocomplete_fields = ("course", "student")
