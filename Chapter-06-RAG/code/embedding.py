import ollama

embeddings = ollama.embed(
  model="embeddinggemma",
  input="Here's a text about cookies"
)
print(len(embeddings['embeddings'][0]))  # vector length
print(embeddings['embeddings'][0][:5])  # first 5 dimensions of the vector