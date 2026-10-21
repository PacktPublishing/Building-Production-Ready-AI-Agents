from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

DB_DIR = Path(__file__).resolve().parent / "chroma_db"

print("✅ Creating client")
client = chromadb.PersistentClient(
    path=str(DB_DIR),
    settings=Settings(anonymized_telemetry=False),
)

collection = client.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"}  # ✅ cosine similarity
)

# Load the same embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve(query: str, k: int = 3):
    if collection.count() == 0:
        return []

    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    documents = results["documents"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    return [
        {"rank": index + 1, "id": doc_id, "distance": distance, "document": document}
        for index, (doc_id, distance, document) in enumerate(zip(ids, distances, documents))
    ]

# Example query
query = "What is cosine similarity used for?"

print("✅ Running retrieval...")
print(f"✅ Looking in: {DB_DIR}")
print(f"✅ Collection contains {collection.count()} documents.")
retrieved_docs = retrieve(query)

print("🔍 Retrieved context:")
if not retrieved_docs:
    print("- No documents found. Run vector-chroma-ingest.py first.")
for result in retrieved_docs:
    print(f"- rank={result['rank']} distance={result['distance']:.4f} id={result['id']}")
    print(f"  {result['document']}")

if retrieved_docs:
    best_match = retrieved_docs[0]
    print("\n✅ Most relevant document:")
    print(f"- id={best_match['id']} distance={best_match['distance']:.4f}")
    print(f"  {best_match['document']}")
