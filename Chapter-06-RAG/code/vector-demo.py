from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownTextSplitter
import os

model = "embeddinggemma"
vector_store_path = "vector_store.json"

def log(msg: str):
    print(f"[LOG] {msg}")

# Create embeddings using Ollama
embeddings = OllamaEmbeddings(model=model)

# Load existing vector store or create new one
if os.path.exists(vector_store_path):
    log(f"Loading vector store from {vector_store_path}...")
    vector_store = InMemoryVectorStore.load(vector_store_path, embeddings)
else:
    log("Creating new vector store...")
    vector_store = InMemoryVectorStore(embeddings)

    # split sample.md
    with open('sample.md', 'r') as file:
        text = file.read()

    # run text splitter
    chunks = MarkdownTextSplitter(chunk_size=500).split_text(text)
    log(f"Split document into {len(chunks)} chunks")

    # Add chunks to vector store (embeddings created automatically)
    log("Adding chunks to the vector store...")
    vector_store.add_texts(chunks)
    
    # Save to disk
    log(f"Saving vector store to {vector_store_path}...")
    vector_store.dump(vector_store_path)

# user prompt
prompt = "What are the requirements for installing WidgetX 3000?"
log(f"Query: {prompt}")

# Set minimum similarity threshold (0-1, higher = more strict)
threshold = 0.7

# search for the most similar chunk (embedding + search done automatically)
log("Searching for the most similar chunk...")
results = vector_store.similarity_search_with_score(prompt, k=1)

doc, score = results[0]
if score >= threshold:
    log(f"Most similar chunk (similarity: {score:.4f}):")
    print(doc.page_content)
else:
    log(f"No relevant chunk found (best score: {score:.4f} < threshold: {threshold})")
