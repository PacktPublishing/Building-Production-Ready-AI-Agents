from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownTextSplitter
import os

model = "embeddinggemma"
vector_store_path = "vector_store_metadata.json"
threshold = 0.3

def log(msg: str):
    print(f"[LOG] {msg}")

def ingest(source_file: str = os.path.join(os.path.dirname(__file__), "docs", "sample.md")):
    """Ingest a markdown document into the vector store."""
    embeddings = OllamaEmbeddings(model=model)
    
    if os.path.exists(vector_store_path):
        log(f"Loading vector store from {vector_store_path}...")
        vector_store = InMemoryVectorStore.load(vector_store_path, embeddings)
    else:
        log("Creating new vector store...")
        vector_store = InMemoryVectorStore(embeddings)

        # Read and split the markdown file
        with open(source_file, 'r') as file:
            text = file.read()

        chunks = MarkdownTextSplitter(chunk_size=500).split_text(text)
        log(f"Split document into {len(chunks)} chunks")

        # Create metadata for each chunk
        metadatas = [
            {"source": source_file, "chunk_index": i} 
            for i in range(len(chunks))
        ]

        # Add chunks to vector store
        log("Adding chunks to the vector store...")
        vector_store.add_texts(chunks, metadatas=metadatas)
        
        # Save to disk
        log(f"Saving vector store to {vector_store_path}...")
        vector_store.dump(vector_store_path)
    
    return vector_store

def get_chunks(source_file: str = os.path.join(os.path.dirname(__file__), "docs", "sample.md")):
    """Return all chunks from the source document."""
    with open(source_file, 'r') as file:
        text = file.read()
    return MarkdownTextSplitter(chunk_size=500).split_text(text)

def search(prompt: str, vector_store: InMemoryVectorStore = None):
    """Search the vector store for chunks similar to the prompt. Returns (content, chunk_index) or (None, -1)."""
    if vector_store is None:
        embeddings = OllamaEmbeddings(model=model)
        vector_store = InMemoryVectorStore.load(vector_store_path, embeddings)
    
    log(f"Query: {prompt}")
    log("Searching for the most similar chunk...")
    
    results = vector_store.similarity_search_with_score(prompt, k=1)
    
    if not results:
        log("No results found")
        return None, -1
    
    doc, score = results[0]
    if score >= threshold:
        chunk_index = doc.metadata.get('chunk_index', -1)
        log(f"Most similar chunk (similarity: {score:.4f}):")
        log(f"Source: {doc.metadata.get('source', 'unknown')}, Chunk: {chunk_index}")
        return doc.page_content, chunk_index
    else:
        log(f"No relevant chunk found (best score: {score:.4f} < threshold: {threshold})")
        return None, -1

if __name__ == "__main__":
    # Ingest documents
    vector_store = ingest()
    
    # Search with a prompt
    prompt = "What are the requirements for installing WidgetX 3000?"
    result, chunk_index = search(prompt, vector_store)
    if result:
        print(f"Matched chunk {chunk_index}:")
        print(result)
