import os
import faiss
import pickle
from typing import List, Tuple
import numpy as np

BASE_DATA_DIR = "data"

class VectorStore:
    def __init__(self, repo_identifier: str, dim: int = 384):
        self.dim = dim
        self.repo_identifier = repo_identifier

        # Per-repo folder
        self.repo_dir = os.path.join(BASE_DATA_DIR, repo_identifier)
        self.index_path = os.path.join(self.repo_dir, "faiss.index")
        self.meta_path = os.path.join(self.repo_dir, "metadata.pkl")

        os.makedirs(self.repo_dir, exist_ok=True)

        self.index = faiss.IndexFlatL2(dim)
        self.metadata = []

        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self._load()

    def add(self, vectors: List[List[float]], metadata: List[dict]):
        np_vectors = np.array(vectors).astype("float32")
        self.index.add(np_vectors)
        self.metadata.extend(metadata)

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)

    def search(self, query_vector: List[float], k: int = 5) -> List[Tuple[dict, float]]:
        # Check if index is empty or metadata is missing
        if self.index.ntotal == 0 or not self.metadata:
            return []
        
        query = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(query, k)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            # Check for valid index: non-negative and within metadata bounds
            if idx >= 0 and idx < len(self.metadata):
                results.append((self.metadata[idx], dist))
            # Optionally, skip invalid indices silently
            # If you want to log this, add: print(f"Skipping invalid index {idx} with distance {dist}")
        return results

    def clear(self):
        """Clear current index and metadata (e.g., before indexing new repo)"""
        self.index = faiss.IndexFlatL2(self.dim)
        self.metadata = []

    def _load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            self.metadata = pickle.load(f)