from django.contrib import admin

from .models import Conversation, KnowledgeArticle, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content", "created_at"]
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "created_at", "updated_at"]
    inlines = [MessageInline]


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "updated_at"]
    list_filter = ["category"]
    search_fields = ["title", "content"]
