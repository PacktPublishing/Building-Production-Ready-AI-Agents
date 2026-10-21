import numpy as np

def cosine_similarity(vecA, vecB):
    dot_product = np.dot(vecA, vecB)
    magnitudeA = np.linalg.norm(vecA)
    magnitudeB = np.linalg.norm(vecB)
    
    if magnitudeA == 0 or magnitudeB == 0:
        return 0.0  # Avoid division by zero
    
    return dot_product / (magnitudeA * magnitudeB)

# Example usage
vecA = np.array([0.25, 0.1, 0.75, 0.5])
vecB = np.array([0.2, 0.15, 0.7, 0.55])
similarity = cosine_similarity(vecA, vecB)
print(similarity)