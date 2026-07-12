"""HuggingFace Transformers-based Embedding Engine with centralized CacheManager and batched PyTorch encoding."""
import os
import hashlib
import numpy as np
import torch
from typing import List
from services.legal_ai.cache_manager import CacheManager

class LocalSentenceEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.cache_manager = CacheManager()
        self._load_model()

    def _load_model(self):
        """Attempts to load transformers model. Falls back gracefully if offline."""
        try:
            from transformers import AutoTokenizer, AutoModel
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.eval()
            self.use_fallback = False
        except Exception as e:
            print(f"Transformers Model load fallback: {e}")
            self.use_fallback = True

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def get_embedding(self, text: str) -> List[float]:
        """Generate 384-dimensional embedding for a single text string with cache lookup."""
        cached = self.cache_manager.get("embedding", text)
        if cached:
            return cached

        if self.use_fallback:
            np.random.seed(int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16) % (2**32))
            emb = np.random.normal(0, 1, 384)
            emb = (emb / np.linalg.norm(emb)).tolist()
        else:
            try:
                inputs = self.tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
                with torch.no_grad():
                    model_output = self.model(**inputs)
                sentence_embeddings = self._mean_pooling(model_output, inputs['attention_mask'])
                sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
                emb = sentence_embeddings[0].cpu().numpy().tolist()
            except Exception:
                np.random.seed(len(text))
                emb = np.random.normal(0, 1, 384)
                emb = (emb / np.linalg.norm(emb)).tolist()

        self.cache_manager.set("embedding", text, emb)
        return emb

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in optimized PyTorch batches, utilizing centralized caching."""
        results = [None] * len(texts)
        miss_indices = []
        miss_texts = []
        
        for idx, t in enumerate(texts):
            cached = self.cache_manager.get("embedding", t)
            if cached:
                results[idx] = cached
            else:
                miss_indices.append(idx)
                miss_texts.append(t)
                
        if miss_texts:
            if self.use_fallback:
                for idx, t in zip(miss_indices, miss_texts):
                    emb = self.get_embedding(t)
                    results[idx] = emb
            else:
                try:
                    inputs = self.tokenizer(miss_texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
                    with torch.no_grad():
                        model_output = self.model(**inputs)
                    sentence_embeddings = self._mean_pooling(model_output, inputs['attention_mask'])
                    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
                    
                    embs = sentence_embeddings.cpu().numpy().tolist()
                    for idx, t, emb in zip(miss_indices, miss_texts, embs):
                        self.cache_manager.set("embedding", t, emb)
                        results[idx] = emb
                except Exception as ex:
                    print(f"Batch embedding failed: {ex}. Falling back to single embedding.")
                    for idx, t in zip(miss_indices, miss_texts):
                        results[idx] = self.get_embedding(t)
                        
        return results
