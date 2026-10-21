import sqlite3
import sqlite_vec
import struct
import ollama
from langchain_text_splitters import MarkdownTextSplitter

model = "embeddinggemma"
db_path = "vector_store.db"

def log(msg: str):
    print(f"[LOG] {msg}")

def serialize_vector(vector: list[float]) -> bytes:
    """Serialize a vector to bytes for storage in SQLite."""
    return struct.pack(f"{len(vector)}f", *vector)

def deserialize_vector(blob: bytes) -> list[float]:
    """Deserialize bytes back to a vector."""
    return list(struct.unpack(f"{len(blob)//4}f", blob))

def create_db():
    """Create the database and vector table."""
    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT,
            chunk_index INTEGER,
            embedding BLOB
        )
    """)
    
    # Create virtual table for vector similarity search
    # Get embedding dimension from a test embedding
    test_embedding = ollama.embed(model=model, input="test")['embeddings'][0]
    dim = len(test_embedding)
    
    db.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding float[{dim}] distance_metric=cosine
        )
    """)
    
    db.commit()
    return db

def add_chunk(db, content: str, source: str, chunk_index: int):
    """Add a chunk with its embedding to the database."""
    # Generate embedding
    embedding = ollama.embed(model=model, input=content)['embeddings'][0]
    
    # Insert into chunks table
    cursor = db.execute(
        "INSERT INTO chunks (content, source, chunk_index, embedding) VALUES (?, ?, ?, ?)",
        (content, source, chunk_index, serialize_vector(embedding))
    )
    chunk_id = cursor.lastrowid
    
    # Insert into vector table
    db.execute(
        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
        (chunk_id, serialize_vector(embedding))
    )
    
    db.commit()
    return chunk_id

def similarity_search(db, query: str, top_k: int = 1):
    """Search for most similar chunks to the query."""
    # Generate query embedding
    query_embedding = ollama.embed(model=model, input=query)['embeddings'][0]
    
    # Search using vector similarity (KNN query requires k = ? syntax)
    results = db.execute("""
        SELECT 
            c.id,
            c.content,
            c.source,
            c.chunk_index,
            v.distance
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.chunk_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
    """, (serialize_vector(query_embedding), top_k)).fetchall()
    
    return results

def get_chunk_count(db) -> int:
    """Get the number of chunks in the database."""
    return db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

# Main execution
log("Connecting to SQLite vector database...")
db = create_db()

# Check if we need to ingest data
if get_chunk_count(db) == 0:
    log("Database empty, ingesting document...")
    
    # Split sample.md
    source_file = "sample.md"
    with open(source_file, 'r') as file:
        text = file.read()
    
    # Run text splitter
    chunks = MarkdownTextSplitter(chunk_size=500).split_text(text)
    log(f"Split document into {len(chunks)} chunks")
    
    # Add chunks to database
    log("Adding chunks to vector database...")
    for i, chunk in enumerate(chunks):
        add_chunk(db, chunk, source_file, i)
        log(f"  Added chunk {i+1}/{len(chunks)}")
    
    log("Ingestion complete!")
else:
    log(f"Database already contains {get_chunk_count(db)} chunks")

# User prompt
prompt = "What are the requirements for installing WidgetX 3000?"
log(f"Query: {prompt}")

# Set minimum similarity threshold
threshold = 0.7

# Search for similar chunks
log("Searching for similar chunks...")
results = similarity_search(db, prompt, top_k=1)

if results:
    chunk_id, content, source, chunk_index, distance = results[0]
    # Convert cosine distance to similarity (distance 0 = identical, 2 = opposite)
    # Cosine similarity = 1 - distance
    similarity = 1 - distance
    
    if similarity >= threshold:
        log(f"Most similar chunk (similarity: {similarity:.4f}):")
        log(f"Source: {source}, Chunk: {chunk_index}")
        print(content)
    else:
        log(f"No relevant chunk found (best similarity: {similarity:.4f} < threshold: {threshold})")
else:
    log("No results found")

db.close()
