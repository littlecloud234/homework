from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.qa.views import ChatPageView


def healthz(request):
    """轻量健康检查，供负载均衡与容器探针使用。"""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("healthz/", healthz, name="healthz"),
    path("", ChatPageView.as_view(), name="chat"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.knowledge.urls")),
    path("api/v1/", include("apps.qa.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
