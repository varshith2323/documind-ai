
from chatbot.document_processor import process_pdf
from chatbot.vector_store import create_vector_store, search_documents

# Step 1: Extract and split the sample PDF.
chunks = process_pdf("sample_handbook.pdf")

print(f"Indexing {len(chunks)} document chunk(s)...")

# Step 2: Generate embeddings and save the chunks.
create_vector_store(chunks)

print("Document indexed successfully.")

# Step 3: Search the saved vector database.
question = "How much annual leave do employees receive?"
results = search_documents(question, k=3)

print("\nRetrieved results:")

for result in results:
    print(f"\nPage: {result.metadata.get('page', 'Unknown')}")
    print(result.page_content)
