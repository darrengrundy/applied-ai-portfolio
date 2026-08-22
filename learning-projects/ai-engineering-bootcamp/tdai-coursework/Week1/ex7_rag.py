"""
Exercise: Retrieval-Augmented Generation (RAG)
This script demonstrates how to ground the model's answer in private context.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# Get config from environment variables
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize Azure AI Foundry client (OpenAI-compatible v1 endpoint)
client = OpenAI(
    base_url=ENDPOINT_URL,
    api_key=AZURE_OPENAI_API_KEY
)

# 1. Our 'Private' Knowledge Base (Information the model wasn't trained on)
internal_document = """
The 2026 Galactic Games were held on Mars. 
The gold medal for 'Low-Gravity Sprinting' was won by an athlete named Jax Zoop. 
The games were sponsored by 'Nebula Coffee'.
"""

def demo_rag(query):
    print(f"\n--- RAG Demo ---")
    print(f"User Question: {query}")
    # In a real RAG system, we would search a database for the right text.
    # Here, we manually 'augment' the prompt with our document.
    prompt = f"""
    Use the following piece of context to answer the question. 
    If the answer isn't in the context, say 'I do not have that information.'
    
    CONTEXT:
    {internal_document}
    
    QUESTION: 
    {query}
    """
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"\nAI Response (Grounded in Context):\n{response.choices[0].message.content}")

if __name__ == "__main__":
    # Test the RAG system
    demo_rag("Who won the gold medal and who sponsored the event?")
