from rest_framework import serializers

from .models import Message


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "created_at"]
