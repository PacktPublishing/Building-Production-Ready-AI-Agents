import argparse
from pathlib import Path
from typing import Any, Literal

import ollama
from graphqlite import graph
from pydantic import BaseModel

MODEL = "llama3.1:latest"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "my_graph.db"
DOMAIN_PATH = BASE_DIR / "data" / "domain.txt"


def log(message: str) -> None:
    print(f"[LOG] {message}")


class Entity(BaseModel):
    type: str
    name: str


class Relationship(BaseModel):
    from_entity: str
    to_entity: str
    type: str


class KnowledgeGraph(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]


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


class QueryResponse(BaseModel):
    prompt: str
    plan: QueryPlan
    cypher: str
    rows: list[dict[str, Any]]
    answer: str


def make_node_id(entity_type: str, name: str) -> str:
    normalized_type = entity_type.strip().lower()
    normalized_name = "-".join(name.strip().lower().split())
    return f"{normalized_type}-{normalized_name}"


def normalize_entity_type(entity_type: str, name: str, relationships: list[Relationship]) -> str:
    normalized_type = entity_type.strip().lower()
    if normalized_type != "person":
        return normalized_type.capitalize()

    directed_movie = any(
        rel.from_entity == name and rel.type.strip().lower().replace("_", " ") in {"directed", "directed by"}
        for rel in relationships
    )
    acted_in_movie = any(
        rel.from_entity == name
        and rel.type.strip().lower().replace("_", " ") in {"acted in", "acted in by"}
        for rel in relationships
    )

    if directed_movie:
        return "Director"
    if acted_in_movie:
        return "Actor"
    return "Person"


def normalize_relationship(rel_type: str, from_type: str, to_type: str) -> tuple[str, str, str]:
    normalized_type = rel_type.strip().lower().replace("_", " ")

    if normalized_type in {"directed", "directed by"}:
        return "DIRECTED_BY", "Movie", "Director"
    if normalized_type in {"acted in", "acted in by"}:
        return "ACTED_IN", "Movie", "Actor"
    if normalized_type == "genre":
        return "BELONGS_TO_GENRE", "Movie", "Genre"

    return normalized_type.upper().replace(" ", "_"), from_type, to_type


def load_domain_text() -> str:
    log("Loading text from domain.txt...")
    with open(DOMAIN_PATH, "r", encoding="utf-8") as file:
        return file.read()


def extract_knowledge_graph(text: str) -> KnowledgeGraph:
    prompt = f"""
Extract the entities and relationships from the following text:
{text}

Use only these entity types: Movie, Director, Actor, Genre.
Use only these relationship types and directions:
- Movie -> DIRECTED_BY -> Director
- Movie -> ACTED_IN -> Actor
- Movie -> BELONGS_TO_GENRE -> Genre

For each relationship, 'from_entity' is the Movie name and 'to_entity' is the related entity name.
"""

    log("Extracting data for knowledge graph...")
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=KnowledgeGraph.model_json_schema(),
    )

    return KnowledgeGraph.model_validate_json(response.message.content)


def insert_knowledge_graph(db, data: KnowledgeGraph) -> None:
    log("Inserting data into the graph database...")
    entity_type_by_name: dict[str, str] = {}

    for entity in data.entities:
        normalized_type = normalize_entity_type(entity.type, entity.name, data.relationships)
        entity_type_by_name[entity.name] = normalized_type

    for rel in data.relationships:
        edge_type, source_type, target_type = normalize_relationship(
            rel.type,
            entity_type_by_name.get(rel.from_entity, "Person"),
            entity_type_by_name.get(rel.to_entity, "Person"),
        )
        if edge_type in {"DIRECTED_BY", "ACTED_IN", "BELONGS_TO_GENRE"}:
            entity_type_by_name.setdefault(rel.from_entity, source_type)
            entity_type_by_name.setdefault(rel.to_entity, target_type)

    for entity_name, entity_type in entity_type_by_name.items():
        properties = {"name": entity_name}
        if entity_type == "Movie":
            properties = {"title": entity_name}
        db.upsert_node(make_node_id(entity_type, entity_name), properties, entity_type)

    for rel in data.relationships:
        from_type = entity_type_by_name.get(rel.from_entity, "Person")
        to_type = entity_type_by_name.get(rel.to_entity, "Person")
        edge_type, source_type, target_type = normalize_relationship(rel.type, from_type, to_type)

        if edge_type in {"DIRECTED_BY", "ACTED_IN", "BELONGS_TO_GENRE"}:
            source_id = make_node_id(source_type, rel.from_entity)
            target_id = make_node_id(target_type, rel.to_entity)
        else:
            source_id = make_node_id(from_type, rel.from_entity)
            target_id = make_node_id(to_type, rel.to_entity)

        db.upsert_edge(source_id, target_id, {}, edge_type)

    db.connection.commit()
    log("Data inserted successfully!")


def reset_graph_database(db_path: Path = DB_PATH) -> None:
    if db_path.exists():
        db_path.unlink()


def escape_cypher_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_cypher(plan: QueryPlan) -> str:
    if plan.intent == "actors_in_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for actors_in_movie")
        movie_title = escape_cypher_string(plan.movie_title)
        return (
            "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) "
            f"WHERE m.title = '{movie_title}' "
            "RETURN m.title AS movie, a.name AS actor "
            "LIMIT 10"
        )

    if plan.intent == "director_of_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for director_of_movie")
        movie_title = escape_cypher_string(plan.movie_title)
        return (
            "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) "
            f"WHERE m.title = '{movie_title}' "
            "RETURN m.title AS movie, d.name AS director "
            "LIMIT 10"
        )

    if plan.intent == "genre_of_movie":
        if not plan.movie_title:
            raise ValueError("A movie title is required for genre_of_movie")
        movie_title = escape_cypher_string(plan.movie_title)
        return (
            "MATCH (m:Movie)-[:BELONGS_TO_GENRE]->(g:Genre) "
            f"WHERE m.title = '{movie_title}' "
            "RETURN m.title AS movie, g.name AS genre "
            "LIMIT 10"
        )

    if plan.intent == "movies_for_actor":
        if not plan.person_name:
            raise ValueError("A person name is required for movies_for_actor")
        person_name = escape_cypher_string(plan.person_name)
        return (
            "MATCH (m:Movie)-[:ACTED_IN]->(a:Actor) "
            f"WHERE a.name = '{person_name}' "
            "RETURN a.name AS actor, m.title AS movie "
            "LIMIT 10"
        )

    if plan.intent == "movies_for_director":
        if not plan.person_name:
            raise ValueError("A person name is required for movies_for_director")
        person_name = escape_cypher_string(plan.person_name)
        return (
            "MATCH (m:Movie)-[:DIRECTED_BY]->(d:Director) "
            f"WHERE d.name = '{person_name}' "
            "RETURN d.name AS director, m.title AS movie "
            "LIMIT 10"
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


def format_query_rows(plan: QueryPlan, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "I could not find an answer in the graph."

    if plan.intent == "director_of_movie":
        row = rows[0]
        return f"{row['director']} directed {row['movie']}."

    if plan.intent == "genre_of_movie":
        row = rows[0]
        return f"{row['movie']} belongs to the {row['genre']} genre."

    if plan.intent == "actors_in_movie":
        movie = rows[0]["movie"]
        actors = ", ".join(row["actor"] for row in rows)
        return f"The actors I found for {movie} are {actors}."

    if plan.intent == "movies_for_actor":
        actor = rows[0]["actor"]
        movies = ", ".join(row["movie"] for row in rows)
        return f"{actor} appears in {movies}."

    if plan.intent == "movies_for_director":
        director = rows[0]["director"]
        movies = ", ".join(row["movie"] for row in rows)
        return f"{director} directed {movies}."

    return "I found matching rows in the graph."


def seed_graph_database(force_reseed: bool = False, db_path: Path = DB_PATH) -> KnowledgeGraph:
    if force_reseed:
        reset_graph_database(db_path)

    text = load_domain_text()
    data = extract_knowledge_graph(text)

    log("Entities:")
    for entity in data.entities:
        log(f"  [{entity.type}] {entity.name}")

    log("Relationships:")
    for rel in data.relationships:
        log(f"  {rel.from_entity} --[{rel.type}]--> {rel.to_entity}")

    with graph(str(db_path)) as db:
        insert_knowledge_graph(db, data)

    return data


def query_graph(user_prompt: str, db_path: Path = DB_PATH) -> QueryResponse:
    if not user_prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if not db_path.exists():
        raise FileNotFoundError("Graph database not found. Seed the graph first.")

    log("Translating prompt to query plan...")
    plan = translate_prompt_to_plan(user_prompt)
    cypher = build_cypher(plan)

    log("Executing Cypher query...")
    with graph(str(db_path)) as db:
        raw_rows = db.query(cypher)

    rows = [dict(row) for row in raw_rows]
    answer = format_query_rows(plan, rows)

    return QueryResponse(
        prompt=user_prompt,
        plan=plan,
        cypher=cypher,
        rows=rows,
        answer=answer,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the movie graph database from data/domain.txt.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not delete the existing database file before seeding.",
    )
    args = parser.parse_args()

    data = seed_graph_database(force_reseed=not args.no_reset)
    print("Graph seeded successfully.")
    print(f"Entities: {len(data.entities)}")
    print(f"Relationships: {len(data.relationships)}")


if __name__ == "__main__":
    main()