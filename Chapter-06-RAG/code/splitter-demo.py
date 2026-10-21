import ollama
import numpy as np
from langchain_text_splitters import MarkdownTextSplitter

model = "embeddinggemma"

def markdown_text_splitter(text, chunk_size=500):
    splitter = MarkdownTextSplitter(chunk_size=chunk_size)
    chunks = splitter.split_text(text)
    return chunks

def log(str: str):
    print(f"[LOG] {str}")

def cosine_similarity(vecA, vecB):
    dot_product = np.dot(vecA, vecB)
    magnitudeA = np.linalg.norm(vecA)
    magnitudeB = np.linalg.norm(vecB)
    
    if magnitudeA == 0 or magnitudeB == 0:
        return 0.0  # Avoid division by zero
    
    return dot_product / (magnitudeA * magnitudeB)

log("Splitting the text into chunks...")

with open('sample.md', 'r') as file:
    text = file.read()
chunks = markdown_text_splitter(text)
log(f"Created {len(chunks)} chunks.")
# create embeddings for the chunks
log("Creating embeddings for the chunks...")
chunk_embeddings = [ollama.embed(model=model, input=chunk)['embeddings'][0] for chunk in chunks]
# user input
user_question = "What are the requirements for installing WidgetX 3000?"
# embed the user question
log("Embedding the user question...")
question_embedding = ollama.embed(model=model, input=user_question)['embeddings'][0]
# calculate similarity between user question and each chunk
log("Calculating cosine similarity between the user question and each chunk...")
similarities = [cosine_similarity(question_embedding, chunk_embedding) for chunk_embedding in chunk_embeddings]
# find the most similar chunk
most_similar_chunk_index = np.argmax(similarities)
most_similar_chunk = chunks[most_similar_chunk_index]
print(f"Most similar chunk:\n{most_similar_chunk} with similarity {similarities[most_similar_chunk_index]}")
