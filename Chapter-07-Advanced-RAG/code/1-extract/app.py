from pydantic import BaseModel
import ollama


def log(str:str):
    print(f"[LOG] {str}")

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

log("Loading text from data.txt...")
with open("data.txt", "r") as file:
    text = file.read()

prompt = f"""
Extract the entities and relationships from the following text:
{text}

For each relationship, 'from_entity' is the source entity name and 'to_entity' is the target entity name.
"""

log("Sending prompt to model...")
response = ollama.chat(
    model="phi3:mini",
    messages=[{"role": "user", "content": prompt}],
    format=KnowledgeGraph.model_json_schema(),
)

result = KnowledgeGraph.model_validate_json(response.message.content)

log("Entities:")
for entity in result.entities:
    log(f"  [{entity.type}] {entity.name}")

log("Relationships:")
for rel in result.relationships:
    log(f"  {rel.from_entity} --[{rel.type}]--> {rel.to_entity}")

