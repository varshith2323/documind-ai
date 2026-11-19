import logging
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def process_pdf(file_path, max_pages=50):
    """Extract text from a PDF and split into searchable chunks.
    Limits to max_pages to prevent timeouts on large documents.
    """
    reader = PdfReader(file_path)
    documents = []
    total_pages = len(reader.pages)
    pages_to_process = min(total_pages, max_pages)

    if total_pages > max_pages:
        logger.warning(
            "PDF has %d pages; processing first %d pages to prevent timeout.",
            total_pages, max_pages
        )

    # Step 1: Extract text from each page.
    for page_number in range(1, pages_to_process + 1):
        try:
            page = reader.pages[page_number - 1]
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    Document(
                        page_content=text,
                        metadata={"page": page_number}
                    )
                )
        except Exception as e:
            logger.warning("Failed to extract text from page %d: %s", page_number, e)

    if not documents:
        raise ValueError(
            "No extractable text found in this PDF. "
            "It may be scanned or empty."
        )

    # Step 2: Split the extracted text into semantically useful chunks.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
    )

    chunks = splitter.split_documents(documents)
    return chunks
