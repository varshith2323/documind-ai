from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_pdf(file_path):
    """Extract text from a PDF, using OCR for scanned pages, and split into searchable chunks."""

    reader = PdfReader(file_path)
    documents = []

    # Step 1: Extract text from each page; fallback to OCR when needed.
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={"page": page_number}
                )
            )
        else:
            # Attempt OCR for pages without extractable text.
            try:
                from pdf2image import convert_from_path
                from pytesseract import image_to_string
                # Convert only the current page to an image.
                images = convert_from_path(file_path, first_page=page_number, last_page=page_number)
                if images:
                    ocr_text = image_to_string(images[0])
                    if ocr_text.strip():
                        documents.append(
                            Document(
                                page_content=ocr_text,
                                metadata={"page": page_number, "ocr": True}
                            )
                        )
            except Exception as e:
                # Log OCR failures but continue.
                import logging
                logging.getLogger(__name__).warning(
                    f"OCR failed for page {page_number}: {e}"
                )

    if not documents:
        raise ValueError(
            "No extractable text found in this PDF. "
            "It may be scanned or empty."
        )

    # Step 2: Split the extracted text into smaller chunks.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        length_function=len,
    )

    chunks = splitter.split_documents(documents)

    return chunks
