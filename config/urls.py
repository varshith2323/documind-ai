from django.contrib import admin
from django.urls import path
from chatbot import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("ask/", views.ask_question, name="ask_question"),
    path("upload/", views.upload_document, name="upload_document"),

    # User Authentication APIs
    path("api/user/", views.user_status, name="user_status"),
    path("api/register/", views.user_register, name="user_register"),
    path("api/login/", views.user_login, name="user_login"),
    path("api/logout/", views.user_logout, name="user_logout"),

    # Chat Sessions & History APIs
    path("api/chats/", views.list_chat_sessions, name="list_chat_sessions"),
    path("api/chats/new/", views.create_chat_session, name="create_chat_session"),
    path("api/chats/<int:session_id>/", views.chat_session_detail, name="chat_session_detail"),

    # Document Management APIs
    path("api/documents/", views.list_documents, name="list_documents"),
]
