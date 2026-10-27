from django.db import models
from django.contrib.auth.models import User


class UploadedDocument(models.Model):
    """Tracks uploaded PDF documents and their indexing details."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
        null=True,
        blank=True,
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.BigIntegerField(default=0)
    chunks_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.filename} ({self.chunks_count} chunks)"

    @property
    def formatted_size(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class ChatSession(models.Model):
    """Represents a conversation session between a user and DocuMind AI."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Chat #{self.id}: {self.title}"


class ChatMessage(models.Model):
    """Individual user question or assistant response in a chat session."""
    SENDER_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    text = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:40]}"
