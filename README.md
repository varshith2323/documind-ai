# DocuMind AI 🧠📄

> **Intelligent, Grounded Document Question-Answering & Assistant Platform**  
> Built with **Django**, **LangChain**, **Chroma Vector Store**, and **Google Gemini AI**.

DocuMind AI allows teams and individuals to upload company handbooks, contracts, policies, and research documents, then ask questions in natural language and receive strictly grounded, verifiable answers with exact page citations and excerpts.

---

## ✨ Features

- **Document Indexing & Knowledge Base**:
  - Upload PDF files directly from the web interface (supports up to 10 MB per file).
  - Automatic text extraction using `pypdf` with OCR fallback for scanned pages.
  - Smart text chunking with `RecursiveCharacterTextSplitter` (400 chars, 80 overlap).
  - SHA-256 fingerprinting to prevent redundant indexing of duplicate documents.
  - Sidebar Knowledge Base listing all indexed documents with file size and chunk counts.

- **Strictly Grounded RAG (Retrieval-Augmented Generation)**:
  - Vector embeddings powered by Google Gemini (`gemini-embedding-001`) stored in ChromaDB.
  - **Adaptive Relevance Filtering**: Prunes chunks with low confidence or dynamic score drops, preventing irrelevant sections from polluting answers.
  - **Source Attribution & Deduplication**: Only the exact sources directly cited by the model are displayed, eliminating duplicate or unreferenced citations.
  - Anti-hallucination instructions: If the document doesn't contain the answer, the assistant clearly states it rather than inventing information.

- **User Authentication**:
  - User registration, login, and logout powered by Django's secure authentication system.
  - Session claiming: Any conversations created before logging in are automatically linked to your account upon signing in.
  - Displays user profile badge and sign-out controls in the sidebar.

- **Persistent Multi-Session Chat History**:
  - Store and resume multiple conversations across browser sessions.
  - Auto-titles conversation threads based on the first question asked.
  - Reload past conversation messages along with verified source citations.
  - Delete past conversation threads with a single click.

- **Sleek, Responsive UI**:
  - Modern dual-pane interface (dark collapsible sidebar + clean chat stream).
  - Interactive suggestion chips for quick testing.
  - Collapsible document uploader drawer with real-time indexing feedback.
  - Visual citation cards with document name, page number, and source excerpts.

---

## 🏗️ Architecture

```
documind-ai/
├── config/                  # Django project configuration
│   ├── settings.py          # Settings, installed apps, media root
│   ├── urls.py              # Root URL routing
│   └── wsgi.py              # WSGI entry point
├── chatbot/                 # Core AI application
│   ├── models.py            # UploadedDocument, ChatSession, ChatMessage
│   ├── views.py             # Auth, Chat history, Upload, and Ask APIs
│   ├── rag_pipeline.py      # Grounded generation with Gemini & source attribution
│   ├── vector_store.py      # Chroma vector DB, embeddings & adaptive search
│   ├── document_processor.py# PDF text extraction & chunking with OCR fallback
│   ├── admin.py             # Django admin model registration
│   ├── templates/chatbot/   # Single-page responsive application UI
│   │   └── index.html
│   └── migrations/          # Database migrations
├── media/documents/         # Stored PDF uploads
├── chroma_db/               # Persistent Chroma vector store
├── .env                     # API keys and environment variables
├── requirements.txt         # Python package dependencies
└── manage.py                # Django CLI management script
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: 3.11, 3.12, or 3.13
- **Google Gemini API Key**: Obtain a key from [Google AI Studio](https://aistudio.google.com/).

### 2. Clone and Setup Environment

```powershell
# Navigate to project directory
cd documind-ai

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory (if not already present):

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Apply Database Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 6. (Optional) Create Superuser for Admin Panel

```powershell
python manage.py createsuperuser
```

### 7. Run the Development Server

```powershell
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 📖 How to Use

1. **Upload a PDF**:
   - Click the **"Upload Document"** button in the top right header.
   - Choose any PDF document (e.g. employee handbook, policy, contract).
   - Click **"Index PDF"**. You will receive confirmation showing the number of text chunks created.
2. **Ask Questions**:
   - Type your question in the bottom input bar (e.g., *"What is the annual leave policy?"*).
   - Press **Enter** or click **Ask**.
3. **Inspect Citations**:
   - Verified answers display expandable **"Relevant Sources"** cards showing the exact document name, page number, and source passage excerpt.
4. **Sign In & Save History**:
   - Click **"Sign In / Register"** in the lower sidebar.
   - Register a new account or sign in to keep all uploaded documents and chat conversations permanently saved to your user profile.
5. **Manage Conversations**:
   - Click **"+ New Conversation"** to start a fresh thread.
   - Click any conversation title in the sidebar to review past discussions.
   - Hover over a conversation and click `×` to delete it.

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Main single-page application UI |
| `POST` | `/ask/` | Submit a question and receive grounded RAG answer |
| `POST` | `/upload/` | Upload and index a new PDF document |
| `GET` | `/api/user/` | Check current user authentication status |
| `POST` | `/api/register/` | Register a new user account |
| `POST` | `/api/login/` | Log in with username and password |
| `POST` | `/api/logout/` | Log out current session |
| `GET` | `/api/chats/` | List all conversation sessions for user |
| `POST` | `/api/chats/new/` | Create a new conversation session |
| `GET` | `/api/chats/<id>/` | Fetch all messages and citations for a session |
| `DELETE` | `/api/chats/<id>/` | Delete a conversation session |
| `GET` | `/api/documents/` | List all indexed documents in knowledge base |

---

## 🔒 Security & Best Practices

- **CSRF Protection**: All `POST` / `DELETE` requests require the standard Django `X-CSRFToken` header.
- **Strict Grounding**: The LLM system prompt forces strict reliance on retrieved context with negative-fallback handling to prevent hallucinated answers.
- **Safe Uploads**: Uploaded files are renamed using unique UUID prefixes to prevent filename collision or path traversal vulnerabilities.
- **Size Limits**: PDF uploads are capped at 10 MB per document.

---

## 📄 License
This project is licensed under the MIT License.

