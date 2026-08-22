"""
Exercise: Tokenization
This script shows how text is split into tokens (the basic units LLMs use).
"""
import tiktoken

def demo_tokenization(text):
    # Load the encoding for the GPT-4 / GPT-3.5 models
    encoding = tiktoken.get_encoding("cl100k_base")
    # 1. Turn text into Token IDs (the numbers the AI sees)
    tokens = encoding.encode(text)
    # 2. Turn those IDs back into text chunks to see the "cuts"
    chunks = [encoding.decode_single_token_bytes(t).decode('utf-8') for t in tokens]
    print(f"--- Tokenization Demo ---")
    print(f"Original Text: '{text}'")
    print(f"\n1. How the AI 'cuts' the text (Chunks):")
    print(f"   {chunks}")
    print(f"\n2. How the AI 'sees' the text (Token IDs):")
    print(f"   {tokens}")
    print(f"\nTotal Token Count: {len(tokens)}")

# Test with a simple word and a complex word
if __name__ == "__main__":
    demo_tokenization("Tokenization is helpful.")
    print("-" * 30)
    demo_tokenization("antidisestablishmentarianism")
