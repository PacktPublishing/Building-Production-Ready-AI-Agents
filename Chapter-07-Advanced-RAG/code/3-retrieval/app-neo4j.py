import os
from typing import Literal

import ollama
from neo4j import GraphDatabase
from pydantic import BaseModel

MODEL = "phi3:mini"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password1234")


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


def seed_graph(session) -> None:
    session.run("""
        MERGE (m1:Movie {title: 'Inception'})
        MERGE (m2:Movie {title: 'Interstellar'})
        MERGE (d:Director {name: 'Christopher Nolan'})
        MERGE (a1:Actor {name: 'Leonardo DiCaprio'})
        MERGE (a2:Actor {name: 'Matthew McConaughey'})
        MERGE (g:Genre {name: 'SciFi'})
        MERGE (m1)-[:DIRECTED_BY]->(d)
        MERGE (m1)-[:ACTED_IN]->(a1)
        MERGE (m1)-[:BELONGS_TO_GENRE]->(g)
        MERGE (m2)-[:DIRECTED_BY]->(d)
        MERGE (m2)-[:ACTED_IN]->(a2)
        MERGE (m2)-[:BELONGS_TO_GENRE]->(g)
    """)


def build_cypher(plan: QueryPlan) -> tuple[str, dict]:
    if plan.intent == "actors_in_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for actors_in_movie")
        return (
            "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) "
            "WHERE m.title = $movie_title "
            "RETURN m.title AS movie, a.name AS actor "
            "LIMIT 10",
            {"movie_title": plan.movie_title},
        )

    if plan.intent == "director_of_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for director_of_movie")
        return (
            "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) "
            "WHERE m.title = $movie_title "
            "RETURN m.title AS movie, d.name AS director "
            "LIMIT 10",
            {"movie_title": plan.movie_title},
        )

    if plan.intent == "genre_of_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for genre_of_movie")
        return (
            "MATCH (m:Movie)-[:BELONGS_TO_GENRE]->(g:Genre) "
            "WHERE m.title = $movie_title "
            "RETURN m.title AS movie, g.name AS genre "
            "LIMIT 10",
            {"movie_title": plan.movie_title},
        )

    if plan.intent == "movies_for_actor":
        if not plan.person_name:
            raise ValueError("A person name is required for movies_for_actor")
        return (
            "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) "
            "WHERE a.name = $person_name "
            "RETURN a.name AS actor, m.title AS movie "
            "LIMIT 10",
            {"person_name": plan.person_name},
        )

    if plan.intent == "movies_for_director":
        if not plan.person_name:
            raise ValueError("A person name is required for movies_for_director")
        return (
            "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) "
            "WHERE d.name = $person_name "
            "RETURN d.name AS director, m.title AS movie "
            "LIMIT 10",
            {"person_name": plan.person_name},
        )

    raise ValueError(f"Unsupported intent: {plan.intent}")


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


def main() -> None:
    user_prompt = input("Ask a question about the movie graph: ").strip()
    if not user_prompt:
        print("Please enter a question.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        log("Seeding graph data...")
        seed_graph(session)

        log("Translating prompt to query plan...")
        plan = translate_prompt_to_plan(user_prompt)
        cypher, params = build_cypher(plan)

        print("Query plan:")
        print(plan.model_dump())
        print("Generated Cypher:")
        print(cypher)

        log("Executing Cypher query...")
        result = session.run(cypher, params)
        rows = [dict(record) for record in result]

        log("Results:")
        if not rows:
            print("No results found.")
            driver.close()
            return

        for row in rows:
            print(row)

    driver.close()


if __name__ == "__main__":
    main()
