import os
import uuid
import hashlib
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

# Store our vector database inside the project directory.
VECTOR_STORE_PATH = "chroma_db"
COLLECTION_NAME = "documind_documents"


def get_embeddings():
    """Create the Gemini embedding model."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the .env file."
        )

    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=api_key,
    )


def document_already_indexed(file_hash):
    """Check whether a PDF has already been indexed."""
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=VECTOR_STORE_PATH,
    )

    results = vector_store.get(
        where={"file_hash": file_hash},
        limit=1,
    )

    return len(results["ids"]) > 0


def create_vector_store(chunks, source_name="unknown", file_hash=None):
    """Add document chunks while preventing duplicate PDF indexing."""
    if not chunks:
        raise ValueError("No document chunks were provided.")

    if not file_hash:
        raise ValueError("A document hash is required.")

    if document_already_indexed(file_hash):
        return {
            "status": "duplicate",
            "chunks": 0,
        }

    embeddings = get_embeddings()

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=VECTOR_STORE_PATH,
    )

    document_ids = []

    for chunk in chunks:
        chunk.metadata["source"] = source_name
        chunk.metadata["file_hash"] = file_hash
        document_ids.append(str(uuid.uuid4()))

    vector_store.add_documents(
        documents=chunks,
        ids=document_ids,
    )

    return {
        "status": "indexed",
        "chunks": len(chunks),
    }


def search_documents(question, k=3):
    """Retrieve relevant chunks with adaptive relevance filtering and deduplication."""
    embeddings = get_embeddings()

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=VECTOR_STORE_PATH,
    )

    # Search with relevance scores, asking for extra candidates to allow filtering
    candidate_k = max(k * 2, 6)
    results = vector_store.similarity_search_with_relevance_scores(
        question,
        k=candidate_k,
    )

    if not results:
        return []

    # Sort results strictly descending by relevance score
    results.sort(key=lambda item: item[1], reverse=True)

    best_score = results[0][1]

    # If even the best matching chunk has very low similarity, return empty
    if best_score < 0.40:
        return []

    filtered_documents = []
    seen_texts = []

    for document, score in results:
        # Base confidence filter: reject chunks with low relevance
        if score < 0.52:
            continue

        # Relative drop filter: don't pull in chunks that score significantly lower
        # than the top hit (this prevents irrelevant sections from getting included)
        if (best_score - score) > 0.08 and score < (best_score * 0.88):
            continue

        # Text normalization for deduplication
        raw_text = document.page_content.strip()
        normalized = " ".join(raw_text.split()).casefold()

        # Check for substantial text overlap with already accepted chunks
        is_duplicate = False
        for seen in seen_texts:
            # Identical or near-complete substring overlap
            if normalized in seen or seen in normalized:
                is_duplicate = True
                break

            # Check overlap similarity
            shorter_len = min(len(normalized), len(seen))
            if shorter_len > 60:
                common_len = len(set(normalized.split()) & set(seen.split()))
                total_words = len(set(normalized.split()))
                if total_words > 0 and (common_len / total_words) > 0.75:
                    is_duplicate = True
                    break

        if is_duplicate:
            continue

        seen_texts.append(normalized)
        document.metadata["relevance_score"] = float(score)
        filtered_documents.append(document)

        if len(filtered_documents) >= k:
            break

    return filtered_documents
