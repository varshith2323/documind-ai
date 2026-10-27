from chatbot.document_processor import process_pdf

chunks = process_pdf("sample_handbook.pdf")

print(f"Total chunks created: {len(chunks)}")

for index, chunk in enumerate(chunks, start=1):
    print(f"\nChunk {index}")
    print(f"Page: {chunk.metadata['page']}")
    print(f"Text: {chunk.page_content[:200]}")