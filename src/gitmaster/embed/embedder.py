import os
from typing import List, Tuple
from gitmaster.utils.network import is_online
from gitmaster.auth.keymanager import get_openai_key

# Local embedding
from sentence_transformers import SentenceTransformer

# Optional OpenAI (only if available)
try:
    import openai
except ImportError:
    openai = None

# Initialize local model once
_local_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_with_openai(texts: List[str], api_key: str) -> List[List[float]]:
    if not openai:
        raise ImportError("OpenAI SDK not installed. Run `pip install openai`.")

    openai.api_key = api_key
    response = openai.Embedding.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [r["embedding"] for r in response["data"]]


def embed_with_local_model(texts: List[str]) -> List[List[float]]:
    return _local_model.encode(texts, convert_to_numpy=True).tolist()


def embed_chunks(chunks: List[Tuple[str, str]]) -> List[Tuple[List[float], str]]:
    """
    Embeds content chunks using OpenAI or local model.
    Returns a list of (embedding, metadata).
    """
    texts = [chunk[0] for chunk in chunks]
    metadata = [chunk[1] for chunk in chunks]

    api_key = get_openai_key()
    if is_online() and api_key:
        try:
            print("🌐 Using OpenAI for embedding...")
            vectors = embed_with_openai(texts, api_key)
        except Exception as e:
            print(f"⚠️ OpenAI failed, falling back to local model: {e}")
            vectors = embed_with_local_model(texts)
    else:
        print("📴 Offline mode or missing OpenAI key. Using local model.")
        vectors = embed_with_local_model(texts)

    return list(zip(vectors, metadata))
