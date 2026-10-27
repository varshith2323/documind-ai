import hashlib
import json
import logging
import os
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST, require_GET

from chatbot.document_processor import process_pdf
from chatbot.models import UploadedDocument, ChatSession, ChatMessage
from chatbot.rag_pipeline import generate_answer
from chatbot.vector_store import create_vector_store, document_already_indexed

logger = logging.getLogger(__name__)


def _get_or_create_session(request, session_id=None):
    """Retrieve an existing ChatSession or create a new one for the current user/session."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    if session_id:
        try:
            if request.user.is_authenticated:
                return ChatSession.objects.get(id=session_id, user=request.user)
            else:
                return ChatSession.objects.get(id=session_id, session_key=session_key)
        except ChatSession.DoesNotExist:
            pass

    # Create new session
    if request.user.is_authenticated:
        return ChatSession.objects.create(user=request.user, title="New Conversation")
    else:
        return ChatSession.objects.create(session_key=session_key, title="New Conversation")


def home(request):
    """Display the DocuMind AI chat page."""
    return render(request, "chatbot/index.html")


# ============================================================================
# USER AUTHENTICATION APIS
# ============================================================================

@require_GET
def user_status(request):
    """Check current authentication status."""
    if request.user.is_authenticated:
        return JsonResponse({
            "authenticated": True,
            "username": request.user.username,
            "email": request.user.email,
        })
    return JsonResponse({
        "authenticated": False,
        "username": None,
    })


@require_POST
def user_register(request):
    """Register a new user account and log them in."""
    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "")
        email = data.get("email", "").strip()

        if not username or not password:
            return JsonResponse(
                {"error": "Username and password are required."},
                status=400,
            )

        if len(password) < 4:
            return JsonResponse(
                {"error": "Password must be at least 4 characters."},
                status=400,
            )

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse(
                {"error": "A user with this username already exists."},
                status=400,
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
        )
        login(request, user)

        # Claim any anonymous sessions created with this session_key
        if request.session.session_key:
            ChatSession.objects.filter(
                session_key=request.session.session_key,
                user__isnull=True,
            ).update(user=user)

            UploadedDocument.objects.filter(
                user__isnull=True,
            ).update(user=user)

        return JsonResponse({
            "success": True,
            "username": user.username,
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data."}, status=400)
    except Exception as e:
        logger.exception("Registration failed")
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
def user_login(request):
    """Log in an existing user."""
    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return JsonResponse(
                {"error": "Please enter both username and password."},
                status=400,
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            return JsonResponse(
                {"error": "Invalid username or password."},
                status=400,
            )

        login(request, user)

        # Claim anonymous session records
        if request.session.session_key:
            ChatSession.objects.filter(
                session_key=request.session.session_key,
                user__isnull=True,
            ).update(user=user)

        return JsonResponse({
            "success": True,
            "username": user.username,
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data."}, status=400)
    except Exception as e:
        logger.exception("Login failed")
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
def user_logout(request):
    """Log out the current user."""
    logout(request)
    return JsonResponse({"success": True})


# ============================================================================
# CHAT SESSIONS & HISTORY APIS
# ============================================================================

@require_GET
def list_chat_sessions(request):
    """List all conversation sessions for the current user."""
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        sessions = ChatSession.objects.filter(user=request.user)
    else:
        sessions = ChatSession.objects.filter(session_key=request.session.session_key)

    data = [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.strftime("%b %d, %H:%M"),
            "updated_at": s.updated_at.strftime("%b %d, %H:%M"),
            "message_count": s.messages.count(),
        }
        for s in sessions
    ]

    return JsonResponse({"sessions": data})


@require_POST
def create_chat_session(request):
    """Start a new chat conversation."""
    session = _get_or_create_session(request)
    return JsonResponse({
        "id": session.id,
        "title": session.title,
    })


@require_http_methods(["GET", "DELETE"])
def chat_session_detail(request, session_id):
    """Retrieve messages for a session or delete the session."""
    if not request.session.session_key:
        request.session.create()

    try:
        if request.user.is_authenticated:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        else:
            session = ChatSession.objects.get(id=session_id, session_key=request.session.session_key)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Chat session not found."}, status=404)

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"success": True})

    # GET: Return all messages in this session
    messages = [
        {
            "id": m.id,
            "sender": m.sender,
            "text": m.text,
            "sources": m.sources,
            "created_at": m.created_at.strftime("%H:%M"),
        }
        for m in session.messages.all()
    ]

    return JsonResponse({
        "id": session.id,
        "title": session.title,
        "messages": messages,
    })


# ============================================================================
# DOCUMENT MANAGEMENT APIS
# ============================================================================

@require_GET
def list_documents(request):
    """List all saved/uploaded documents."""
    # Ensure existing sample files in media/documents are indexed in DB if DB was freshly created
    if not UploadedDocument.objects.exists():
        upload_dir = os.path.join(settings.MEDIA_ROOT, "documents")
        if os.path.exists(upload_dir):
            for fname in os.listdir(upload_dir):
                if fname.lower().endswith(".pdf"):
                    fpath = os.path.join(upload_dir, fname)
                    try:
                        fsize = os.path.getsize(fpath)
                        # Display clean name without leading hex uuid if present
                        display_name = fname
                        if "_" in fname and len(fname.split("_")[0]) == 32:
                            display_name = "_".join(fname.split("_")[1:])

                        # Calculate hash
                        sha = hashlib.sha256()
                        with open(fpath, "rb") as f:
                            for b in iter(lambda: f.read(8192), b""):
                                sha.update(b)
                        fhash = sha.hexdigest()

                        if not UploadedDocument.objects.filter(file_hash=fhash).exists():
                            UploadedDocument.objects.create(
                                filename=display_name,
                                file_path=fpath,
                                file_hash=fhash,
                                file_size=fsize,
                                chunks_count=2, # reasonable default for sample
                            )
                    except Exception:
                        pass

    if request.user.is_authenticated:
        docs = UploadedDocument.objects.filter(user=request.user)
        # If user has no docs yet, also show documents with user=None (system/sample docs)
        if not docs.exists():
            docs = UploadedDocument.objects.all()
    else:
        docs = UploadedDocument.objects.all()

    data = [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.formatted_size,
            "chunks": d.chunks_count,
            "uploaded_at": d.uploaded_at.strftime("%b %d, %Y"),
        }
        for d in docs
    ]

    return JsonResponse({"documents": data})


# ============================================================================
# RAG QUESTION ANSWERING & UPLOAD APIS
# ============================================================================

@require_POST
def ask_question(request):
    """Receive a question, save to chat history, and return grounded RAG answer."""
    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()
        session_id = data.get("session_id")

        if not question:
            return JsonResponse(
                {"error": "Please enter a question."},
                status=400,
            )

        # Get or create active chat session
        session = _get_or_create_session(request, session_id=session_id)

        # Auto-title conversation if default
        if session.title in ["New Conversation", "New Chat"]:
            # Truncate cleanly for title
            new_title = question[:40].strip()
            if len(question) > 40:
                new_title += "..."
            session.title = new_title
            session.save(update_fields=["title", "updated_at"])

        # Record user message in DB
        ChatMessage.objects.create(
            session=session,
            sender="user",
            text=question,
        )

        # Run RAG retrieval & generation
        result = generate_answer(question)

        # Record assistant response in DB
        ChatMessage.objects.create(
            session=session,
            sender="assistant",
            text=result["answer"],
            sources=result.get("sources", []),
        )

        return JsonResponse({
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "session_id": session.id,
            "session_title": session.title,
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid request data."},
            status=400,
        )

    except Exception:
        logger.exception("Question answering failed")
        return JsonResponse(
            {"error": "Unable to generate an answer. Please try again."},
            status=500,
        )


@require_POST
def upload_document(request):
    """Upload a PDF, save metadata to DB, detect duplicates, and index contents."""
    uploaded_file = request.FILES.get("document")

    if not uploaded_file:
        return JsonResponse(
            {"error": "Please select a PDF file."},
            status=400,
        )

    if not uploaded_file.name.lower().endswith(".pdf"):
        return JsonResponse(
            {"error": "Only PDF files are supported."},
            status=400,
        )

    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse(
            {"error": "The maximum file size is 10 MB."},
            status=400,
        )

    safe_name = os.path.basename(uploaded_file.name)
    upload_dir = os.path.join(settings.MEDIA_ROOT, "documents")
    os.makedirs(upload_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_dir, stored_name)

    try:
        with open(file_path, "wb+") as destination:
            for block in uploaded_file.chunks():
                destination.write(block)

        # Calculate a fingerprint of the file contents
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as pdf_file:
            for block in iter(lambda: pdf_file.read(8192), b""):
                sha256.update(block)

        file_hash = sha256.hexdigest()

        # Check if already indexed in vector database
        if document_already_indexed(file_hash):
            # Ensure UploadedDocument record exists in DB
            existing_doc = UploadedDocument.objects.filter(file_hash=file_hash).first()
            chunk_num = existing_doc.chunks_count if existing_doc else 0
            if not existing_doc:
                UploadedDocument.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    filename=safe_name,
                    file_path=file_path,
                    file_hash=file_hash,
                    file_size=uploaded_file.size,
                    chunks_count=chunk_num,
                )

            return JsonResponse({
                "message": "This document has already been indexed.",
                "filename": safe_name,
                "chunks": chunk_num,
                "duplicate": True,
            })

        chunks = process_pdf(file_path)
        chunk_count = len(chunks)
        logger.info(
            "Extracted %d chunks from %s (hash=%s)",
            chunk_count, safe_name, file_hash,
        )

        if chunk_count == 0:
            return JsonResponse(
                {"error": "No text could be extracted from this PDF."},
                status=400,
            )

        # Index in Chroma vector store
        result = create_vector_store(
            chunks,
            source_name=safe_name,
            file_hash=file_hash,
        )

        # Save document metadata in database
        UploadedDocument.objects.create(
            user=request.user if request.user.is_authenticated else None,
            filename=safe_name,
            file_path=file_path,
            file_hash=file_hash,
            file_size=uploaded_file.size,
            chunks_count=chunk_count,
        )

        return JsonResponse({
            "message": "Document uploaded and indexed successfully.",
            "filename": safe_name,
            "chunks": chunk_count,
            "duplicate": False,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)

    except Exception:
        logger.exception("Document upload and indexing failed")
        return JsonResponse(
            {"error": "Document processing failed. Check the Django terminal."},
            status=500,
        )
