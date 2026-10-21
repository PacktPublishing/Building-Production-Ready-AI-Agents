import argparse
from itertools import combinations

import ollama
import numpy as np

def cosine_similarity(vecA, vecB):
    dot_product = np.dot(vecA, vecB)
    magnitudeA = np.linalg.norm(vecA)
    magnitudeB = np.linalg.norm(vecB)
    
    if magnitudeA == 0 or magnitudeB == 0:
        return 0.0  # Avoid division by zero
    
    return dot_product / (magnitudeA * magnitudeB)

parser = argparse.ArgumentParser(description="Compare text embeddings with cosine similarity.")
parser.add_argument("terms", nargs="*", help="Two or more terms to compare.")
parser.add_argument("--model", default="embeddinggemma", help="Ollama embedding model.")
args = parser.parse_args()

terms = args.terms or ["Banana", "Apple", "Fruit", "Car"]
if len(terms) < 2:
    parser.error("provide at least two terms")

embeddings = {
    term: ollama.embed(model=args.model, input=term)['embeddings'][0]
    for term in terms
}

print(f"Model: {args.model}")
for first_term, second_term in combinations(terms, 2):
    similarity = cosine_similarity(embeddings[first_term], embeddings[second_term])
    print(f"Cosine similarity between '{first_term}' and '{second_term}': {similarity}")
