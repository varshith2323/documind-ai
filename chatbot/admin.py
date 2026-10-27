from django.contrib import admin
from chatbot.models import UploadedDocument, ChatSession, ChatMessage


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "chunks_count", "file_size", "uploaded_at")
    list_filter = ("uploaded_at", "user")
    search_fields = ("filename", "file_hash")


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "updated_at")
    list_filter = ("created_at", "user")
    search_fields = ("title",)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "sender", "short_text", "created_at")
    list_filter = ("sender", "created_at")

    def short_text(self, obj):
        return obj.text[:60]
    short_text.short_description = "Message"
