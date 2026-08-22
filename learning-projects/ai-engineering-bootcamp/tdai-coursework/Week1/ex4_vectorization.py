"""
Exercise: Vectorization
This script demonstrates how to get vector embeddings for text and compare their similarity.
"""
import os
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

# Get config from environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
EMBEDDING_ENDPOINT_URL = os.getenv("EMBEDDING_ENDPOINT_URL")
EMBEDDING_DEPLOYMENT_NAME = os.getenv("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")
EMBEDDING_API_VERSION = os.getenv("EMBEDDING_API_VERSION", "2023-05-15")

# Separate client for the embedding endpoint
client = AzureOpenAI(
    azure_endpoint=EMBEDDING_ENDPOINT_URL,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=EMBEDDING_API_VERSION
)

def get_embedding(text):
    # 'text-embedding-3-small' is a common, cheap model for vectorization
    response = client.embeddings.create(input=[text], model=EMBEDDING_DEPLOYMENT_NAME)
    return np.array(response.data[0].embedding)

def cosine_similarity(v1, v2):
    # High score (close to 1.0) means the words are 'close' in meaning
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

if __name__ == "__main__":
    # 1. Vectorize different concepts
    vec_apple = get_embedding("apple")
    vec_fruit = get_embedding("fruit")
    vec_truck = get_embedding("truck")
    # 2. Compare them
    score_close = cosine_similarity(vec_apple, vec_fruit)
    score_far = cosine_similarity(vec_apple, vec_truck)
    print(f"--- Vectorization Demo ---")
    print(f"Vector for 'apple' (first 5 dimensions): {vec_apple[:5]}...")
    print(f"Vector length: {len(vec_apple)} dimensions")
    print(f"\nSimilarity between 'apple' and 'fruit': {score_close:.4f}")
    print(f"Similarity between 'apple' and 'truck': {score_far:.4f}")
