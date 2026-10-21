from typing import Literal

import ollama
from graphqlite import graph
from pydantic import BaseModel

MODEL = "phi3:mini"
DB_PATH = "my_graph.db"


class QueryPlan(BaseModel):
    intent: Literal[
        "actors_in_movie",
        "director_of_movie",
        "genre_of_movie",
        "movies_for_actor",
        "movies_for_director",
    ]
    movie_title: str | None = None
    person_name: str | None = None


def log(message: str) -> None:
    print(f"[LOG] {message}")


def seed_graph(db) -> None:
    db.upsert_node("movie-inception", {"title": "Inception"}, "Movie")
    db.upsert_node("movie-interstellar", {"title": "Interstellar"}, "Movie")
    db.upsert_node("director-nolan", {"name": "Christopher Nolan"}, "Director")
    db.upsert_node("actor-dicaprio", {"name": "Leonardo DiCaprio"}, "Actor")
    db.upsert_node("actor-mcconaughey", {"name": "Matthew McConaughey"}, "Actor")
    db.upsert_node("genre-scifi", {"name": "SciFi"}, "Genre")

    db.upsert_edge("movie-inception", "director-nolan", {}, "DIRECTED_BY")
    db.upsert_edge("movie-inception", "actor-dicaprio", {}, "ACTED_IN")
    db.upsert_edge("movie-inception", "genre-scifi", {}, "BELONGS_TO_GENRE")
    db.upsert_edge("movie-interstellar", "director-nolan", {}, "DIRECTED_BY")
    db.upsert_edge("movie-interstellar", "actor-mcconaughey", {}, "ACTED_IN")
    db.upsert_edge("movie-interstellar", "genre-scifi", {}, "BELONGS_TO_GENRE")
    db.connection.commit()


def escape_cypher_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


CYPHER_TEMPLATES = {
    "actors_in_movie": {
        "query": "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) WHERE m.title = '{value}' RETURN m.title AS movie, a.name AS actor LIMIT 10",
        "param": "movie_title",
    },
    "director_of_movie": {
        "query": "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) WHERE m.title = '{value}' RETURN m.title AS movie, d.name AS director LIMIT 10",
        "param": "movie_title",
    },
    "genre_of_movie": {
        "query": "MATCH (m:Movie)-[:BELONGS_TO_GENRE]->(g:Genre) WHERE m.title = '{value}' RETURN m.title AS movie, g.name AS genre LIMIT 10",
        "param": "movie_title",
    },
    "movies_for_actor": {
        "query": "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) WHERE a.name = '{value}' RETURN a.name AS actor, m.title AS movie LIMIT 10",
        "param": "person_name",
    },
    "movies_for_director": {
        "query": "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) WHERE d.name = '{value}' RETURN d.name AS director, m.title AS movie LIMIT 10",
        "param": "person_name",
    },
}


def build_cypher(plan: QueryPlan) -> str:
    if plan.intent not in CYPHER_TEMPLATES:
        raise ValueError(f"Unsupported intent: {plan.intent}")

    template = CYPHER_TEMPLATES[plan.intent]
    param_name = template["param"]
    param_value = getattr(plan, param_name)

    if not param_value:
        raise ValueError(f"A {param_name} is required for {plan.intent}")

    escaped_value = escape_cypher_string(param_value)
    return template["query"].format(value=escaped_value)

def translate_prompt_to_plan(user_prompt: str) -> QueryPlan:
    schema = """
Graph schema:
- Nodes:
  - Movie { id, title }
  - Director { id, name }
  - Actor { id, name }
  - Genre { id, name }
- Relationships:
  - (:Movie)-[:DIRECTED_BY]->(:Director)
  - (:Movie)-[:ACTED_IN]->(:Actor)
  - (:Movie)-[:BELONGS_TO_GENRE]->(:Genre)

Supported intents:
- actors_in_movie: who acted in a movie
- director_of_movie: who directed a movie
- genre_of_movie: what genre a movie belongs to
- movies_for_actor: what movies an actor appeared in
- movies_for_director: what movies a director made

Rules:
- Return JSON only matching the provided schema
- Choose exactly one intent
- Fill movie_title only for movie-based questions
- Fill person_name only for person-based questions
- Do not return Cypher
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You map a user question onto one supported graph query intent. "
                    "Return structured JSON only."
                ),
            },
            {
                "role": "user",
                "content": f"{schema}\nUser question: {user_prompt}",
            },
        ],
        format=QueryPlan.model_json_schema(),
    )

    return QueryPlan.model_validate_json(response.message.content)

def create_response(rows) -> str:
    if not rows:
        return "No results found."

    response_lines = []
    for row in rows:
        line = ", ".join(f"{key}: {value}" for key, value in row.items())
        response_lines.append(line)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions about movies based on database query results. "
                "Use the provided query results to answer the user's question. Be concise and informative."
            ),
        },
        {
            "role": "user",
            "content": "Here are the query results:\n" + "\n".join(response_lines),
        },
    ]

    response = ollama.chat(
        model=MODEL,
        messages=messages,
    )

    return response.message.content

def main() -> None:
    user_prompt = input("Ask a question about the movie graph: ").strip()
    if not user_prompt:
        print("Please enter a question.")
        return

    with graph(DB_PATH) as db:
        log("Seeding graph data...")
        seed_graph(db)

        log("Translating prompt to query plan...")
        plan = translate_prompt_to_plan(user_prompt)
        cypher = build_cypher(plan)

        print("Query plan:")
        print(plan.model_dump())
        print("Generated Cypher:")
        print(cypher)

        log("Executing Cypher query...")
        rows = db.query(cypher)

        log("Results:")
        if not rows:
            print("No results found.")
            return

        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
