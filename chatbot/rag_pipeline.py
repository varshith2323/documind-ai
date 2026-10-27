import re
from langchain_google_genai import ChatGoogleGenerativeAI
from chatbot.vector_store import search_documents


def generate_answer(question):
    """Retrieve document context and generate a grounded answer with precise source attribution."""

    # 1. Retrieve filtered and deduplicated document chunks.
    documents = search_documents(question, k=3)

    if not documents:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents.",
            "sources": [],
        }

    # 2. Build numbered context entries.
    context_parts = []
    for idx, document in enumerate(documents, start=1):
        source_name = document.metadata.get("source", "Document")
        page = document.metadata.get("page", "Unknown")
        context_parts.append(
            f"[Source {idx} | File: {source_name} | Page {page}]\n{document.page_content.strip()}"
        )

    context = "\n\n".join(context_parts)

    # 3. Configure the language model.
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
    )

    # 4. Instruct the LLM with strict grounding and source attribution.
    prompt = f"""You are DocuMind AI, an accurate document question-answering assistant.

Answer the user's question using ONLY the supplied document context.

Rules:
- Give a clear, helpful, and concise answer based strictly on the provided context.
- Do not make up facts or assume anything not explicitly mentioned.
- If the context does not contain enough information to answer the question, say:
  "I couldn't find sufficient information in the uploaded documents to answer this question."
  and on a new line write: USED_SOURCES: NONE
- At the very end of your response, on its own line, you MUST write:
  USED_SOURCES: [comma-separated numbers of the sources you actually used, e.g. 1 or 1, 2 or NONE]
  CRITICAL: Only list source numbers whose text you directly referenced or relied on for your answer.
  Do NOT list source numbers that were not relevant to your answer.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    response = llm.invoke(prompt)

    raw_text = response.content
    if isinstance(raw_text, list):
        raw_text = "\n".join(
            block["text"]
            for block in raw_text
            if isinstance(block, dict) and block.get("type") == "text"
        )

    # 5. Parse USED_SOURCES line and clean the answer text.
    sources = []
    used_indices = []

    used_match = re.search(r"USED_SOURCES:\s*([^\n\r]+)", raw_text, re.IGNORECASE)
    if used_match:
        used_str = used_match.group(1).strip()
        if "none" not in used_str.lower():
            # Extract all numbers
            numbers = re.findall(r"\d+", used_str)
            for num in numbers:
                val = int(num)
                if 1 <= val <= len(documents):
                    used_indices.append(val)

    # Remove the USED_SOURCES directive from the user-facing text
    clean_answer = re.sub(
        r"USED_SOURCES:\s*[^\n\r]+", "", raw_text, flags=re.IGNORECASE
    ).strip()

    # If the answer indicates no information was found, do not return sources
    negative_indicators = [
        "couldn't find sufficient information",
        "could not find sufficient information",
        "couldn't find relevant information",
        "could not find relevant information",
    ]
    is_negative = any(ind in clean_answer.lower() for ind in negative_indicators)

    if not is_negative and used_indices:
        seen_source_keys = set()
        for idx in used_indices:
            doc = documents[idx - 1]
            doc_name = doc.metadata.get("source", "Document")
            page = doc.metadata.get("page", "Unknown")

            # Extract a clean excerpt (up to 250 characters)
            content = doc.page_content.strip()
            excerpt = content[:250] + ("..." if len(content) > 250 else "")

            # Deduplication key based on document, page, and first 60 chars of excerpt
            key = f"{doc_name}::p{page}::{excerpt[:60].lower()}"
            if key in seen_source_keys:
                continue

            seen_source_keys.add(key)
            sources.append({
                "document": doc_name,
                "page": page,
                "excerpt": excerpt,
            })
    elif not is_negative and not used_match and documents:
        # Fallback only if model didn't output USED_SOURCES at all:
        # include only the single highest-scoring chunk
        top_doc = documents[0]
        doc_name = top_doc.metadata.get("source", "Document")
        page = top_doc.metadata.get("page", "Unknown")
        content = top_doc.page_content.strip()
        sources.append({
            "document": doc_name,
            "page": page,
            "excerpt": content[:250] + ("..." if len(content) > 250 else ""),
        })

    return {
        "answer": clean_answer,
        "sources": sources,
    }
