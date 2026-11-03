from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AskView, ConversationViewSet, FeedbackView

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("courses/<int:course_id>/ask/", AskView.as_view(), name="course-ask"),
    path("messages/<int:pk>/feedback/", FeedbackView.as_view(), name="message-feedback"),
    path("", include(router.urls)),
]
