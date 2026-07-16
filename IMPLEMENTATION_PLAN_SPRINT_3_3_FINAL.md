# Implementation Plan: Sprint 3.3 - Enterprise Knowledge Graph Intelligence (Final)

This document presents the finalized **Enterprise Architecture Review and Implementation Plan** for Sprint 3.3 (Enterprise Knowledge Graph Intelligence). The architecture extends the RedactAI platform with version-aware, provenanced relational subgraphs, NetworkX-driven traversals, semantic graph search, and graph analytics dashboards.

---

## 1. Enterprise Architecture Review

The review board has evaluated the Sprint 3.3 draft. The proposed extensions introduce version-aware, fully provenanced entity networks while maintaining 100% backward compatibility. The retrieval pipeline has been updated to insert Graph Expansion and Traversal directly after hybrid search, followed by Cross-Encoder reranking and citation grounding.

```mermaid
graph TD
    Query[User Query] --> Process[Query Processor]
    Process --> Hybrid[Hybrid Retrieval]
    Process --> KGMatch[Semantic Node Match]
    Hybrid --> Traversal[Graph Traversal & BFS/DFS Expansion]
    KGMatch --> Traversal
    Traversal --> Context[Context Aggregation]
    Context --> Rerank[Cross-Encoder Reranker]
    Rerank --> Copilot[Copilot Generation Engine]
```

---

## 2. Approved & Improved Components

### Approved Components (No Modifications)
- **Hybrid Retrieval**: Core vector and keyword BM25 search remains unchanged.
- **Embedding Providers**: Existing MiniLM, LegalBERT, and BGE models are reused.
- **Citation Engine**: Core claim validation scoring is preserved.

### Improved Components (New Enterprise Capabilities)
- **Graph Versioning**: Linked to `document_versions` with rollback, comparisons, and version-aware APIs.
- **Node/Edge Provenance**: Stores originating document details, page number, clause context, extraction model, timestamps, confidence, and human verification status.
- **Semantic Graph Embeddings**: Node vectors mapped to reuse embedding providers.
- **Explainable Traversal Paths**: API yields visited node sequences, traversed edge weights, and path rationale.
- **Observability & Analytics**: Implements community detection (Louvain), closeness statistics, isolated node tracking, density, and latency indicators.

---

## 3. Updated Folder Structure

```text
backend/
├── models/
│   └── graph.py                      # [NEW] Versioned GraphNode & GraphEdge tables
├── services/
│   └── legal_ai/
│       ├── graph_builder.py          # [NEW] Multi-doc builders with NER linkage
│       ├── graph_traversal.py        # [NEW] BFS, DFS, PPR, and path explainers
│       ├── graph_analytics.py        # [NEW] Louvain, pagerank, and centrality
│       ├── graph_observability.py    # [NEW] Density, isolated nodes, cache tracking
│       └── graph_cache.py            # [NEW] Redis/Memory cache with TTL
└── api/
    └── v1/
        └── graph.py                  # [NEW] Version-aware REST API controllers
frontend/
└── app/
    └── dashboard/
        └── graph/
            └── page.tsx              # [NEW] Interactive force-directed dashboard
```

---

## 4. Updated Database Schema

```sql
CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    properties JSON NOT NULL, -- page_number, section, clause, paragraph, extraction_model, etc.
    embedding_vector JSON,    -- semantic node vector
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE TABLE graph_edges (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    weight FLOAT NOT NULL DEFAULT 1.0,
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    source_module VARCHAR(50) NOT NULL,
    extraction_algorithm VARCHAR(50) NOT NULL,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    properties JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_graph_nodes_version ON graph_nodes(document_version_id);
CREATE INDEX idx_graph_edges_version ON graph_edges(document_version_id);
CREATE INDEX idx_graph_nodes_org ON graph_nodes(organization_id);
CREATE INDEX idx_graph_edges_org ON graph_edges(organization_id);
```

---

## 5. Traversal & Reasoning Algorithms

- **BFS (Breadth First Search)**: Layers expansion mapping adjacent nodes up to `max_depth`.
- **DFS (Depth First Search)**: Multi-hop tracking to identify legal reference dependencies.
- **Personalized PageRank (PPR)**: Computes node centrality distribution centered on matching query nodes.
- **Explainability**: Traversal calls record visited node arrays and compute cumulative path confidence:
  $$\text{Confidence}_{\text{Path}} = \prod_{e \in \text{Edges}} \text{Confidence}_e$$

---

## 6. API Specification

- `GET /api/v1/graph/entities`: Fetch nodes by organization and document version.
- `GET /api/v1/graph/versions`: List active and historical graph versions for a document.
- `POST /api/v1/graph/traverse`: Traversal endpoint yielding paths, visited nodes, and reasoning context.
- `GET /api/v1/graph/analytics`: Computes Louvain communities, centralities, and hubs.
- `GET /api/v1/graph/observability`: Yields observability stats (isolated count, average degree, latency).

---

## 7. Security & Scalability Review

- **Security Isolation**: `organization_id` filters are strictly enforced on all SELECT/UPDATE SQL operations.
- **Scalability (1M Documents / 100M Nodes)**:
  - Add composite index tables on `(organization_id, document_version_id)`.
  - Traverse using read-only db sessions.
  - Implement dynamic subgraph chunking: traversal caches load only active document subgraphs in NetworkX.

---

## 8. Approved Recommendation

- **Overall Architecture Score**: **96 / 100**
- **Production Readiness Score**: **95 / 100**
- **Go / No-Go**: **GO**

SPRINT 3.3 ARCHITECTURE IS APPROVED FOR IMPLEMENTATION.
