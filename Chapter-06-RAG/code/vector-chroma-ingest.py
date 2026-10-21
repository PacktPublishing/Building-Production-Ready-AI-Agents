from pathlib import Path
import uuid

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

DB_DIR = Path(__file__).resolve().parent / "chroma_db"

# 1. Create Chroma client (persistent)
print("✅ Creating client")
client = chromadb.PersistentClient(
    path=str(DB_DIR),
    settings=Settings(anonymized_telemetry=False),
)

print("✅ Creating collection with COSINE similarity")
# 2. Create a collection using COSINE similarity
collection = client.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"}  # ✅ cosine similarity
)

# 3. Load embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Example documents (normally PDFs, markdown, etc.)
documents = [
    "ChromaDB is a vector database for embeddings.",
    "RAG stands for Retrieval-Augmented Generation.",
    "Cosine similarity measures the angle between vectors.",
    "LLMs can hallucinate without grounding."
]

# 4. Chunking (simplified)
chunks = documents  # assume already chunked

print("✅ Embedding and inserting documents into ChromaDB...")
# 5. Embed and insert
embeddings = embedder.encode(chunks).tolist()

collection.add(
    ids=[str(uuid.uuid4()) for _ in chunks],
    documents=chunks,
    embeddings=embeddings
)

print("✅ Documents ingested into ChromaDB.")
print(f"✅ Collection now contains {collection.count()} documents.")
print(f"✅ Persisted at: {DB_DIR}")

print("✅ Ingestion complete")

# pip install chromadb sentence-transformers