# Chapter 07 Code Examples

This folder contains the runnable code examples for the Advanced RAG chapter.

## What This Folder Contains

- `1-extract`: extract entities and relationships from plain text using Ollama and structured output
- `2-insert`: create a small graph in `graphqlite` and run a simple query
- `3-retrieval`: translate a natural-language question into a graph query and execute it against either `graphqlite` or Neo4j

## Shared Requirements

- Python 3.12+
- Ollama installed and running locally
- The model `phi3:mini` installed in Ollama

Install the Ollama model if needed:

```bash
ollama pull phi3:mini
```

## Shared Install

From this `code` folder, install dependencies with `uv`:

```bash
uv sync
```

If you prefer `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install graphqlite neo4j ollama pydantic
```

The examples use the dependencies declared in [pyproject.toml](pyproject.toml).

## 1-extract

Folder: [1-extract](1-extract)

### What 1-extract Does

This example reads `data.txt`, sends the content to Ollama, and asks the model to return structured JSON containing:

- entities
- relationships

The script validates that JSON with Pydantic and prints the extracted graph pieces.

Source file:

- [1-extract/app.py](1-extract/app.py)

### Run 1-extract

From inside the `1-extract` folder:

```bash
cd 1-extract
uv run python app.py
```

### Expected Input

- `data.txt` must exist in the same folder
- Ollama must be running locally

### 1-extract Output

The script prints log lines such as:

- entities found in the text
- relationships found in the text

## 2-insert

Folder: [2-insert](2-insert)

### What 2-insert Does

This example inserts a small hard-coded movie graph into a local `graphqlite` database and immediately queries it.

It creates nodes for:

- movie
- director
- actor
- genre

Then it creates graph edges and runs a query to find the director of `Inception`.

Source file:

- [2-insert/app.py](2-insert/app.py)

### Run 2-insert

From inside the `2-insert` folder:

```bash
cd 2-insert
uv run python app.py
```

### 2-insert Output

The script:

- writes to `my_graph.db`
- runs a query
- prints something like `Movie: Inception, Director: Christopher Nolan`

### Notes

- `my_graph.db` is a local file-based graph database created in this folder
- rerunning the script reuses that database file

## 3-retrieval

Folder: [3-retrieval](3-retrieval)

This folder contains two versions of the retrieval example:

- `app.py` for `graphqlite`
- `app-neo4j.py` for Neo4j

### What 3-retrieval Does

These examples show the retrieval step of GraphRAG:

1. seed a small graph
2. accept a natural-language question
3. ask Ollama to convert that question into a structured query plan
4. build a Cypher query from that plan
5. execute the query and print the results

#### Supported question types

- actors in a movie
- director of a movie
- genre of a movie
- movies for an actor
- movies for a director

### 3-retrieval/app.py

Source file:

- [3-retrieval/app.py](3-retrieval/app.py)

#### What 3-retrieval/app.py Uses

- `graphqlite`
- local `my_graph.db`
- Ollama with `phi3:mini`

#### Run 3-retrieval/app.py

From inside the `3-retrieval` folder:

```bash
cd 3-retrieval
uv run python app.py
```

Then enter a question when prompted, for example:

```text
Who directed Inception?
```

#### 3-retrieval/app.py Output

The script prints:

- the structured query plan
- the generated Cypher query
- the query results

### 3-retrieval/app-neo4j.py

Source file:

- [3-retrieval/app-neo4j.py](3-retrieval/app-neo4j.py)

#### What 3-retrieval/app-neo4j.py Uses

- Neo4j instead of `graphqlite`
- Ollama with `phi3:mini`

#### Required Environment Variables

When you first create a Neo4j instance, you are asked to set a username and password. Use those credentials in the configuration below.

The script reads these environment variables:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

Defaults in the script are (my choice of credentials, update to what you choose for username and password):

- `bolt://localhost:7687`
- `neo4j`
- `password1234`

Set them in your shell if your local Neo4j instance uses different values:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
```

#### Run 3-retrieval/app-neo4j.py

From inside the `3-retrieval` folder:

```bash
cd 3-retrieval
uv run python app-neo4j.py
```

Then enter a question when prompted.

#### 3-retrieval/app-neo4j.py Output

The script seeds a Neo4j graph, generates a query plan, executes the query, and prints the matching rows.

## Quick Start

If you only want to try the examples quickly:

1. `uv sync`
2. `ollama pull phi3:mini`
3. `cd 1-extract` then `uv run python app.py`
4. Return to `code`, then `cd 2-insert` and run `uv run python app.py`
5. Return to `code`, then `cd 3-retrieval` and run `uv run python app.py`

## Files At The Root Of code

- [main.py](main.py): placeholder entry point, not one of the chapter examples
- [pyproject.toml](pyproject.toml): shared dependencies for these examples
