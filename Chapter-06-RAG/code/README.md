# Chapter 06 RAG Code Folder

This folder contains runnable, focused demos for Retrieval-Augmented Generation (RAG) building blocks:

- text chunking
- embeddings
- cosine similarity
- in-memory vector search
- persistent vector storage with ChromaDB and SQLite Vec

The examples are intentionally small and independent so you can run one concept at a time.

## Prerequisites

1. Python 3.12+
2. Ollama installed and running locally
3. Embedding model pulled in Ollama:

```powershell
ollama pull embeddinggemma
```

4. Internet access for first-time model/package downloads (for example, Sentence Transformers in Chroma demos)

## Install And Setup

The dependency list is defined in Chapter-06-RAG/pyproject.toml.

Option A (recommended, uv):

```powershell
cd ..
uv sync
cd code
```

Option B (pip + venv):

```powershell
cd ..
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
cd code
```

## Run Scripts

From this folder, run any script with:

```powershell
python .\<script-name>.py
```

Example:

```powershell
python .\embedding.py
```

## Python File Guide

### Core Concepts

- cosine.py
	- Pure NumPy cosine similarity function with a simple hard-coded vector example.
	- No external model calls.

- embedding.py
	- Generates an embedding for one input text using Ollama and prints vector size plus first dimensions.

- cosine-demo.py
	- Creates embeddings for sample words with Ollama, then compares every pair using cosine similarity.
	- Accepts custom terms and an optional `--model` argument for experimenting with different phrases and embedding models.

- text-splitter-markdown.py
	- Uses MarkdownTextSplitter to chunk sample.md and prints each chunk.

- splitter-demo.py
	- End-to-end mini retrieval pipeline:
	- chunk sample.md, embed chunks and query with Ollama, compute cosine similarity, return best chunk.

### Vector Store Demos

- vector-demo.py
	- Uses LangChain InMemoryVectorStore + Ollama embeddings.
	- On first run, splits sample.md and stores vectors in vector_store.json.
	- On later runs, loads existing store and performs similarity search.

- vector-metadata-demo.py
	- Same flow as vector-demo.py, but stores metadata (source file and chunk index) per chunk.
	- Persists data in vector_store_metadata.json.

- vector-sqlite-demo.py
	- Uses SQLite + sqlite-vec extension for persistent vector search.
	- Creates tables, embeds chunks, stores embeddings as BLOB, and runs KNN similarity queries.
	- Persists data in vector_store.db.

### ChromaDB Demos

- chroma-demo.py
	- In-memory Chroma example.
	- Splits sample.md, inserts chunks into a collection, runs a query, and prints the best matching chunk.

- vector-chroma-ingest.py
	- Persistent Chroma ingestion script.
	- Creates/opens local Chroma database in chroma_db, embeds documents with SentenceTransformer, inserts into collection docs.

- vector-chroma-retrieval.py
	- Retrieval companion for vector-chroma-ingest.py.
	- Opens persisted Chroma collection, embeds query, and returns top matches with distances.

## Non-Python Files You Will See

- **sample.md**
	- Source document used by split and retrieval demos.

- **vector_store.json**
	- This is the file created by vector-demo.py on first run, containing the persisted in-memory vector store. Subsequent runs will load from this file instead of re-embedding.
	- Persisted in-memory vector store from vector-demo.py.

- **vector_store_metadata.json**
	- This file will be created by vector-metadata-demo.py on first run, containing the persisted in-memory vector store with metadata. Subsequent runs will load from this file instead of re-embedding.
	- Persisted in-memory vector store with metadata from vector-metadata-demo.py.

- **vector_store.db**
	- For this file, the first run of vector-sqlite-demo.py will create a SQLite database with the embedded chunks stored as BLOBs. 
	- SQLite database used by vector-sqlite-demo.py.

- **chroma_db/**
	- Persistent ChromaDB storage used by vector-chroma-ingest.py and vector-chroma-retrieval.py.

## Notes

- Some scripts auto-create local data files on first run.
- If Ollama is not running, scripts that call ollama.embed will fail.
- If you change embedding models, avoid mixing old/new embeddings in the same persisted store.
