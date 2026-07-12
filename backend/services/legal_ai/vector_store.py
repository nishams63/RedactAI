"""Vector Store Abstraction Interface and Default ChromaDB / Numpy Fallback implementations."""
import os
import uuid
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class VectorStoreInterface(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Add text chunks and corresponding embedding vectors to store."""
        pass

    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Query vector database for similar chunks, returning list of (chunk, score) tuples."""
        pass

    @abstractmethod
    def reset(self):
        """Clear database collection/store contents."""
        pass


class ChromaVectorStore(VectorStoreInterface):
    """Default Vector Store implementing ChromaDB backend."""
    def __init__(self, db_dir: str = None, collection_name: str = "legal_knowledge"):
        if db_dir is None:
            db_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "local_storage",
                "chromadb"
            )
        self.db_dir = db_dir
        self.collection_name = collection_name
        self.use_fallback = False
        
        try:
            import chromadb
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(
                path=self.db_dir,
                settings=Settings(allow_reset=True)
            )
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception as e:
            print(f"ChromaDB initialization failed: {e}. Falling back to NumpyVectorStore.")
            self.use_fallback = True
            self.fallback_store = NumpyVectorStore(db_dir=self.db_dir)

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        if self.use_fallback:
            return self.fallback_store.add_chunks(chunks, embeddings)

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        # Flatten metadatas values to support ChromaDB limitations (no dicts inside metadata)
        flat_metadatas = []
        for meta in metadatas:
            flat_m = {}
            for k, v in meta.items():
                if isinstance(v, list):
                    flat_m[k] = ",".join(v)
                else:
                    flat_m[k] = v
            flat_metadatas.append(flat_m)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=flat_metadatas
        )

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        if self.use_fallback:
            return self.fallback_store.query(query_embedding, top_k)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        output = []
        if results and "ids" in results and results["ids"]:
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(ids)
            metadatas = results["metadatas"][0] if "metadatas" in results else [{}] * len(ids)
            documents = results["documents"][0] if "documents" in results else [""] * len(ids)
            
            for idx in range(len(ids)):
                # Convert distance (L2 distance or similar) to cosine-like score (0 to 1)
                dist = distances[idx]
                score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                
                # Unpack keywords if list
                meta = dict(metadatas[idx])
                if "keywords" in meta and isinstance(meta["keywords"], str):
                    meta["keywords"] = meta["keywords"].split(",")
                
                chunk = {
                    "chunk_id": ids[idx],
                    "text": documents[idx],
                    "metadata": meta
                }
                output.append((chunk, score))
        return output

    def reset(self):
        if self.use_fallback:
            return self.fallback_store.reset()
        try:
            self.client.reset()
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception:
            pass


class NumpyVectorStore(VectorStoreInterface):
    """Fallback vector database using local NumPy matrices and file persistence."""
    def __init__(self, db_dir: str):
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)
        self.storage_file = os.path.join(self.db_dir, "numpy_vectors.npz")
        self.chunks = []
        self.embeddings = []
        self._load()

    def _load(self):
        if os.path.exists(self.storage_file):
            try:
                data = np.load(self.storage_file, allow_pickle=True)
                self.chunks = list(data["chunks"])
                self.embeddings = list(data["embeddings"])
            except Exception:
                self.chunks = []
                self.embeddings = []

    def _save(self):
        np.savez(self.storage_file, chunks=np.array(self.chunks, dtype=object), embeddings=np.array(self.embeddings))

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        existing_ids = {c["chunk_id"] for c in self.chunks}
        for chunk, emb in zip(chunks, embeddings):
            if chunk["chunk_id"] not in existing_ids:
                self.chunks.append(chunk)
                self.embeddings.append(emb)
        self._save()

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        if not self.embeddings:
            return []

        q_vec = np.array(query_embedding)
        norms = np.linalg.norm(self.embeddings, axis=1)
        q_norm = np.linalg.norm(q_vec)
        
        if q_norm == 0:
            similarities = np.zeros(len(self.embeddings))
        else:
            dot_products = np.dot(self.embeddings, q_vec)
            similarities = dot_products / (norms * q_norm + 1e-9)

        # Sort indices desc
        indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in indices:
            results.append((self.chunks[idx], float(similarities[idx])))
        return results

    def reset(self):
        self.chunks = []
        self.embeddings = []
        if os.path.exists(self.storage_file):
            try:
                os.remove(self.storage_file)
            except Exception:
                pass
        self._save()
