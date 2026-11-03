from rest_framework import serializers

from .models import Citation, Conversation, Message


class CitationSerializer(serializers.ModelSerializer):
    chunk_id = serializers.IntegerField(read_only=True, allow_null=True)
    document_title = serializers.CharField(read_only=True)

    class Meta:
        model = Citation
        fields = ("id", "chunk_id", "document_title", "rank", "score", "quote")
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    conversation_id = serializers.IntegerField(read_only=True)
    citations = CitationSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation_id",
            "role",
            "content",
            "status",
            "model_name",
            "prompt_tokens",
            "completion_tokens",
            "latency_ms",
            "created_at",
            "citations",
        )
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "course",
            "course_code",
            "course_title",
            "title",
            "created_at",
            "updated_at",
            "messages",
        )
        read_only_fields = fields


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=1000)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_question(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("问题不能为空。")
        return value


class FeedbackSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=[(1, "有用"), (-1, "没用")])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate(self, attrs):
        attrs.setdefault("comment", "")
        return attrs
