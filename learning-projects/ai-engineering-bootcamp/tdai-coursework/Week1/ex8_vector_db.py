"""
Exercise: Vector Database Search
This script demonstrates how to use a simple vector database (ChromaDB) for semantic search.
"""
import chromadb
from chromadb.utils import embedding_functions

# 1. Setup the 'Database' (In-memory for this demo)
client = chromadb.Client()

# 2. Define the Embedding Function (How we turn text into vectors)
# By default, Chroma uses a light, local model so you don't need an API key for this part!
collection = client.create_collection(name="my_smart_warehouse")

# 3. Add 'Items' to our Warehouse
collection.add(
    documents=[
        "The sun is a star at the center of our solar system.", 
        "A coding language used for data science and AI.",
        "A fast car with a powerful engine and sleek design."
    ],
    ids=["id1", "id2", "id3"]
)

def search_warehouse(query_text):
    print(f"\nSearching for: '{query_text}'")
    # 4. The Magic: Search by meaning, not by keywords
    results = collection.query(
        query_texts=[query_text],
        n_results=1
    )
    print(f"Found match: {results['documents'][0][0]}")
    print(f"Distance Score: {results['distances'][0][0]:.4f} (Lower = Closer match)")

# Notice: The query doesn't use the words 'star', 'coding', or 'car'
if __name__ == "__main__":
    search_warehouse("A vehicle that goes very fast")
    search_warehouse("Programming for machine learning")
