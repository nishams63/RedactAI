"""Versioned Knowledge Ingestion Pipeline for Legal Documents."""
import os
import json
import uuid
import hashlib
from typing import List, Dict, Any

class KnowledgeIngestionPipeline:
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "local_storage",
                "knowledge_base"
            )
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.registry_file = os.path.join(self.storage_dir, "kb_registry.json")
        self._load_registry()

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
            except Exception:
                self.registry = {"versions": {}, "active_version": "v1.0.0"}
        else:
            self.registry = {"versions": {}, "active_version": "v1.0.0"}

    def _save_registry(self):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def ingest_document(
        self,
        title: str,
        content: str,
        source: str,
        section_number: str,
        category: str,
        keywords: List[str],
        version: str = "v1.0.0"
    ) -> Dict[str, Any]:
        """Ingest a single legal document, split it into chunks, generate metadata, and save."""
        doc_id = str(uuid.uuid4())
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # Sliding window chunker with overlap (chunk size = 150 words, overlap = 30 words)
        words = content.split()
        chunk_size = 150
        overlap = 30
        chunks = []
        idx = 0
        chunk_idx = 0
        
        while idx < len(words):
            chunk_words = words[idx : idx + chunk_size]
            text = " ".join(chunk_words)
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "metadata": {
                    "document_id": doc_id,
                    "title": title,
                    "source": source,
                    "section_number": section_number,
                    "category": category,
                    "keywords": keywords,
                    "chunk_index": chunk_idx
                }
            })
            idx += (chunk_size - overlap)
            chunk_idx += 1

        # Save versioned document data
        if version not in self.registry["versions"]:
            self.registry["versions"][version] = {"documents": {}, "chunks": []}

        doc_entry = {
            "id": doc_id,
            "title": title,
            "hash": doc_hash,
            "source": source,
            "section_number": section_number,
            "category": category,
            "keywords": keywords,
            "content": content
        }
        self.registry["versions"][version]["documents"][doc_id] = doc_entry
        
        # Avoid duplicate chunks by text content and chunk_id
        existing_texts = {c["text"].strip().lower() for c in self.registry["versions"][version]["chunks"]}
        existing_chunk_ids = {c["chunk_id"] for c in self.registry["versions"][version]["chunks"]}
        
        for c in chunks:
            text_cleaned = c["text"].strip().lower()
            if c["chunk_id"] not in existing_chunk_ids and text_cleaned not in existing_texts:
                self.registry["versions"][version]["chunks"].append(c)
                existing_texts.add(text_cleaned)

        self._save_registry()
        return doc_entry

    def get_active_chunks(self, version: str = None) -> List[Dict[str, Any]]:
        """Get all chunks for a specific version or the default active version."""
        if not version:
            version = self.registry.get("active_version", "v1.0.0")
        
        if version not in self.registry["versions"]:
            # Bootstrap if empty from default json
            self.bootstrap_default_knowledge(version)
            
        return self.registry["versions"].get(version, {}).get("chunks", [])

    def bootstrap_default_knowledge(self, version: str = "v1.0.0"):
        """Seed initial regulations into versioned database."""
        default_json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "regulations.json"
        )
        if os.path.exists(default_json_path):
            with open(default_json_path, "r", encoding="utf-8") as f:
                regs = json.load(f)
                for reg in regs:
                    self.ingest_document(
                        title=reg["title"],
                        content=reg["content"],
                        source=reg["source"],
                        section_number=reg["section_number"],
                        category=reg["category"],
                        keywords=reg["keywords"],
                        version=version
                    )
        self.registry["active_version"] = version
        self._save_registry()
