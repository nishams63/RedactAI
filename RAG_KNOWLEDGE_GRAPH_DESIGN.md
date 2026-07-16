# Design Document: Graph-Guided Retrieval (Graph RAG) Layer

This document outlines the architectural blueprint for introducing a Knowledge Graph layer to complement RedactAI's current RAG system. This graph layer is designed to act as an additional context-selection signal, enhancing primary Vector/BM25 retrieval without replacing it.

---

## 1. Objectives & Architectural Fit

The goal of the Knowledge Graph layer is to map semantic, structural, and regulatory associations between document sections, entities, and cross-references. 

In a traditional RAG pipeline, chunks are retrieved independently. By overlaying a graph layer, we can reconstruct the broader document layout and retrieve closely connected nodes (e.g., definitions, parent sections, or related regulations) that vector similarity might miss.

```
       ┌──────────────────────┐
       │   User Legal Query   │
       └──────────┬───────────┘
                  │
                  ▼
   ┌─────────────────────────────┐
   │ Primary Retrieval: RRF      │◄── Hybrid Sparse/Dense Search
   │ (Vector + BM25 Chunks)      │
   └──────────────┬──────────────┘
                  │ Top-K Nodes
                  ▼
   ┌─────────────────────────────┐
   │ Graph Traversal Signal      │◄── Traverses adjacent/referenced nodes
   │ (BFS Expansion & PageRank)  │
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌─────────────────────────────┐
   │ Context Selection & Rerank  │─── Compiles expanded grounded context
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌─────────────────────────────┐
   │     Local Qwen 2.5 SLM      │
   └─────────────────────────────┘
```

---

## 2. Graph Schema & Node Types

The graph is modelled as a directed property graph representing the structural hierarchy and legal connections.

### Node Types
1. **Document**: Represents the root document (e.g., `NDA.pdf`).
2. **Section**: Headings or logical chapters (e.g., `Section 4: Indemnification`).
3. **Clause / Chunk**: A specific text chunk containing legal statements or obligations.
4. **Entity**: Named Entities extracted via spaCy NLP / Microsoft Presidio (e.g., `TCS`, `UIDAI`, `Aadhaar`).
5. **Reference**: External regulatory targets (e.g., `DPDP Act Section 8`, `RBI KYC Guidelines`).

### Edge Types (Relationships)
All relationships are directed and stored inside the database layer:
- `PARENT_OF` (Document -> Section -> Clause)
- `NEXT_SIBLING` (Clause A -> Clause B: maintains physical document reading order)
- `MENTIONS_ENTITY` (Clause -> Entity)
- `CROSS_REFERENCES` (Clause -> Clause: internal document link)
- `CITES_REGULATION` (Clause -> Reference: links to statutory guidelines)

---

## 3. Database Layer: Reusing `rag_relationships`

To prevent schema bloat and minimize migration overhead, the existing `rag_relationships` table is reused and extended with property flags.

```sql
-- Conceptual database schema mapping
CREATE TABLE rag_relationships (
    id UUID PRIMARY KEY,
    source_chunk_id UUID REFERENCES rag_chunks(id) ON DELETE CASCADE,
    target_chunk_id UUID REFERENCES rag_chunks(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- 'parent_child', 'next_sibling', 'mentions_entity', 'cites_regulation'
    weight FLOAT DEFAULT 1.0,               -- Connection strength/confidence
    metadata_json JSON,                     -- Stores offset, entity labels, etc.
    created_at TIMESTAMP
);
```

---

## 4. Graph Traversal Algorithms

Graph traversal is executed dynamically during retrieval phases:

1. **Local BFS (Breadth-First Search) Expansion**:
   - For each node in the primary Top-K retrieved list, traverse outgoing and incoming links of type `NEXT_SIBLING` and `PARENT_OF` with a depth of $d=1$.
   - *Purpose:* Automatically pulls preceding legal clauses or definitions that explain the retrieved passage.

2. **Personalized PageRank (PPR)**:
   - Use the primary Top-K candidates as seed nodes (starting distributions) for a random-walk algorithm over the graph.
   - Run a short random walk (3-5 hops) to find adjacent nodes with high semantic connectivity.
   - *Purpose:* Identifies related legal clauses across different documents or chapters that mention the same entities or cite the same regulations.

---

## 5. Integrating Graph Signals in the Retrieval Pipeline

Rather than substituting vector matching, graph signals function as a secondary reranking heuristic.

```
       ┌────────────────────────┐
       │   Primary Candidates   │ (e.g., Chunks C1, C2, C3)
       └───────────┬────────────┘
                   │
                   ├──────────────────────────┐
                   ▼                          ▼
       ┌───────────────────────┐  ┌───────────────────────┐
       │ BFS Struct Expansion  │  │ PPR Semantic Walk     │
       │ (C1 -> Definition C0) │  │ (C2 -> Regulation R1) │
       └───────────┬───────────┘  └───────────┬───────────┘
                   │                          │
                   └───────────┬──────────────┘
                               ▼
                   ┌───────────────────────┐
                   │ Reranking & Fusion    │
                   │ (Boost & Compile)     │
                   └───────────────────────┘
```

### Context Selection Scoring
For each retrieved chunk $C$, compute a composite score:
$$\text{FinalScore}(C) = w_1 \cdot \text{RRF\_Score}(C) + w_2 \cdot \text{Graph\_Centrality}(C)$$
Where:
- $\text{RRF\_Score}(C)$ is the Reciprocal Rank Fusion score of vector search and BM25.
- $\text{Graph\_Centrality}(C)$ is calculated based on the number of inbound references and entity links connected to $C$.
- $w_1 = 0.8$ and $w_2 = 0.2$, guaranteeing that vector/keyword relevance remains the dominant signal while the graph breaks ties or bubbles up high-context definitions.
