const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class AgentsService {
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

  async executeWorkflow(query: string, documentIds: string[] = []) {
    return this.request<any>("/agents/execute", {
      method: "POST",
      body: JSON.stringify({ query, document_ids: documentIds }),
    });
  }

  async getRegistry() {
    return this.request<any[]>("/agents/registry");
  }

  async toggleAgentActivation(agentId: string, version: string, isActive: boolean) {
    return this.request<any>("/agents/registry/toggle", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, version, is_active: isActive }),
    });
  }

  async getHealthMetrics() {
    return this.request<any[]>("/agents/metrics");
  }
}

export const agentsService = new AgentsService();
