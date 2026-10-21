import chromadb
from langchain_text_splitters import MarkdownTextSplitter

def log(msg: str):
    print(f"[LOG] {msg}")

# Read and split the markdown file
source_file = "sample.md"
with open(source_file, 'r') as file:
    text = file.read()

chunks = MarkdownTextSplitter(chunk_size=500).split_text(text)
log(f"Split document into {len(chunks)} chunks")

# Create Chroma client and collection
client = chromadb.Client()
collection = client.create_collection("docs")

# Add chunks with auto-generated IDs
log("Adding chunks to Chroma...")
collection.add(
    documents=chunks, 
    ids=[str(i) for i in range(len(chunks))],
    metadatas=[{"source": source_file, "chunk_index": i} for i in range(len(chunks))]
)

# Query
prompt = "What are the requirements for installing WidgetX 3000?"
log(f"Query: {prompt}")

results = collection.query(query_texts=[prompt], n_results=1)

log(f"Most similar chunk (distance: {results['distances'][0][0]:.4f}):")
log(f"Source: {results['metadatas'][0][0]['source']}")
print(results['documents'][0][0])