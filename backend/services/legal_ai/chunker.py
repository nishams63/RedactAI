import re
from typing import List, Dict, Any

class LegalDocumentChunker:
    """Intelligent legal document chunker implementing paragraph, clause, section, and sliding-window strategies."""

    @staticmethod
    def chunk_by_paragraphs(text: str, doc_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text by double newlines, preserving offset and context wrappers."""
        paragraphs = text.split("\n\n")
        chunks = []
        char_offset = 0
        
        for idx, p in enumerate(paragraphs):
            p_text = p.strip()
            if not p_text or len(p_text) < 15:
                char_offset += len(p) + 2
                continue
                
            start = char_offset
            end = start + len(p_text)
            
            # Context-aware prefixing
            prefix = ""
            if doc_metadata:
                title = doc_metadata.get("title", "Document")
                prefix = f"Context: [Document: {title}] "
                
            chunks.append({
                "chunk_type": "paragraph",
                "text": prefix + p_text,
                "page_number": doc_metadata.get("page_number", 1) if doc_metadata else 1,
                "start_char": start,
                "end_char": end,
                "metadata_json": {
                    "paragraph_index": idx,
                    "original_text": p_text
                }
            })
            char_offset += len(p) + 2
            
        return chunks

    @staticmethod
    def chunk_by_clauses(text: str, doc_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text using legal clause indicators (e.g. numberings, list items, specific key phrases)."""
        # Split by typical legal item indicators: (a), 1., Section X, Article Y, etc.
        pattern = r"(?=\([\w\d]\)\s|[1-9]\.\s|Section\s[0-9]|Article\s[I|V|X])"
        clauses = re.split(pattern, text)
        chunks = []
        char_offset = 0
        
        for idx, cl in enumerate(clauses):
            cl_text = cl.strip()
            if not cl_text or len(cl_text) < 15:
                char_offset += len(cl)
                continue
                
            start = char_offset
            end = start + len(cl_text)
            
            prefix = ""
            if doc_metadata:
                title = doc_metadata.get("title", "Document")
                prefix = f"Context: [Document: {title}] "
                
            chunks.append({
                "chunk_type": "clause",
                "text": prefix + cl_text,
                "page_number": doc_metadata.get("page_number", 1) if doc_metadata else 1,
                "start_char": start,
                "end_char": end,
                "metadata_json": {
                    "clause_index": idx,
                    "original_text": cl_text
                }
            })
            char_offset += len(cl)
            
        return chunks

    @staticmethod
    def chunk_by_sections(text: str, doc_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text by major section titles (e.g. 'SECTION 1', 'ARTICLE II')."""
        pattern = r"(?=\n[S|s]ection\s+[0-9]+\b|\n[A|a]rticle\s+[I|V|X]+\b|\n[A|a]greement\b)"
        sections = re.split(pattern, text)
        chunks = []
        char_offset = 0
        
        for idx, sec in enumerate(sections):
            sec_text = sec.strip()
            if not sec_text or len(sec_text) < 20:
                char_offset += len(sec)
                continue
                
            start = char_offset
            end = start + len(sec_text)
            
            prefix = ""
            if doc_metadata:
                title = doc_metadata.get("title", "Document")
                prefix = f"Context: [Document: {title}] "
                
            chunks.append({
                "chunk_type": "section",
                "text": prefix + sec_text,
                "page_number": doc_metadata.get("page_number", 1) if doc_metadata else 1,
                "start_char": start,
                "end_char": end,
                "metadata_json": {
                    "section_index": idx,
                    "original_text": sec_text
                }
            })
            char_offset += len(sec)
            
        return chunks

    @staticmethod
    def chunk_sliding_window(text: str, chunk_size_words: int = 150, overlap_words: int = 30, doc_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Splits text using overlapping word sliding windows."""
        words = text.split()
        chunks = []
        idx = 0
        chunk_idx = 0
        
        # Simple character position mapping approximation
        word_positions = []
        pos = 0
        for w in words:
            start = text.find(w, pos)
            word_positions.append((start, start + len(w)))
            pos = start + len(w)

        while idx < len(words):
            chunk_words = words[idx : idx + chunk_size_words]
            chunk_text = " ".join(chunk_words)
            
            start_char = word_positions[idx][0]
            end_char = word_positions[min(idx + chunk_size_words - 1, len(words) - 1)][1]
            
            prefix = ""
            if doc_metadata:
                title = doc_metadata.get("title", "Document")
                prefix = f"Context: [Document: {title}] "
                
            chunks.append({
                "chunk_type": "sliding_window",
                "text": prefix + chunk_text,
                "page_number": doc_metadata.get("page_number", 1) if doc_metadata else 1,
                "start_char": start_char,
                "end_char": end_char,
                "metadata_json": {
                    "chunk_index": chunk_idx
                }
            })
            idx += (chunk_size_words - overlap_words)
            chunk_idx += 1
            
        return chunks
