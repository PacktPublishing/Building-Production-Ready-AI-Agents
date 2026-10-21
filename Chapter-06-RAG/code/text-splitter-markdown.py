from langchain_text_splitters import MarkdownTextSplitter
def markdown_text_splitter(text, chunk_size=500):
    splitter = MarkdownTextSplitter(chunk_size=chunk_size)
    chunks = splitter.split_text(text)
    return chunks

with open('sample.md', 'r') as file:
    text = file.read()

chunks = markdown_text_splitter(text)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:\n{chunk}\n")