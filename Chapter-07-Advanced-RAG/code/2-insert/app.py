# pip install graphqlite

# write a simple program that connects, writes and reads from a graph database using graphqlite
from graphqlite import graph


def log(message: str) -> None:
    print(f"[LOG] {message}")


with graph("my_graph.db") as db:
    log("Inserting data into the graph database...")
    db.upsert_node("movie-inception", {"title": "Inception"}, "Movie")
    db.upsert_node("director-nolan", {"name": "Christopher Nolan"}, "Director")
    db.upsert_node("actor-dicaprio", {"name": "Leonardo DiCaprio"}, "Actor")
    db.upsert_node("genre-scifi", {"name": "SciFi"}, "Genre")

    db.upsert_edge("movie-inception", "director-nolan", {}, "DIRECTED_BY")
    db.upsert_edge("movie-inception", "actor-dicaprio", {}, "ACTED_IN")
    db.upsert_edge("movie-inception", "genre-scifi", {}, "BELONGS_TO_GENRE")
    db.connection.commit()

    log("Data inserted successfully!")
    result = db.query("""
    MATCH (m:Movie {id: 'movie-inception'})-[:DIRECTED_BY]->(d:Director)
    RETURN m.title AS movie, d.name AS director
    """)

    log("Query executed successfully!")
    log("Results:")
    for record in result:
        print(f"Movie: {record['movie']}, Director: {record['director']}")
