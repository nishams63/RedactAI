const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class CopilotService {
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

  // --- Chat APIs ---
  async getConversations(params?: { search_query?: string; doc_name?: string }) {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          queryParams.append(key, String(value));
        }
      });
    }
    const query = queryParams.toString();
    return this.request<any[]>(`/copilot/conversations${query ? `?${query}` : ""}`);
  }

  async getConversationDetails(id: string) {
    return this.request<any>(`/copilot/conversations/${id}`);
  }

  async deleteConversation(id: string) {
    return this.request<any>(`/copilot/conversations/${id}`, {
      method: "DELETE",
    });
  }

  // --- SSE Stream Initiator ---
  async chatStream(data: {
    message: string;
    conversation_id?: string;
    document_ids?: string[];
    filters?: any;
  }): Promise<Response> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}/copilot/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response;
  }

  // --- Workspace APIs ---
  async pinWorkspaceItem(data: {
    item_type: string;
    title: string;
    content: string;
    metadata_json?: any;
  }) {
    return this.request<any>("/copilot/workspace/items", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getWorkspaceItems(itemType?: string) {
    const query = itemType ? `?item_type=${itemType}` : "";
    return this.request<any[]>(`/copilot/workspace/items${query}`);
  }

  async deleteWorkspaceItem(id: string) {
    return this.request<any>(`/copilot/workspace/items/${id}`, {
      method: "DELETE",
    });
  }

  // --- Human Review API ---
  async submitHumanReview(
    messageId: string,
    data: {
      reviewer_decision: string;
      edited_answer?: string;
      reviewer_comments?: string;
    }
  ) {
    return this.request<any>(`/copilot/reviews/${messageId}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- Analytics API ---
  async getAnalytics() {
    return this.request<any>("/copilot/analytics");
  }
}

export const copilotService = new CopilotService();
