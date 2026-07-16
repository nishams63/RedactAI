const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class GraphService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_URL;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) || {}),
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getDocumentSubgraph(documentId: string) {
    return this.request<any>(`/graph/document/${documentId}`);
  }

  async getStatistics(documentVersionId?: string) {
    const query = documentVersionId ? `?document_version_id=${documentVersionId}` : "";
    return this.request<any>(`/graph/statistics${query}`);
  }

  async traverseGraph(payload: {
    start_node_id?: string;
    method: "bfs" | "dfs" | "pagerank";
    max_depth?: number;
    document_version_id?: string;
    query_labels?: string[];
  }) {
    return this.request<any>("/graph/traverse", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async queryNodes(query: string, nodeType?: string) {
    return this.request<any>("/graph/query", {
      method: "POST",
      body: JSON.stringify({ query, node_type: nodeType }),
    });
  }
}

export const graphService = new GraphService();
