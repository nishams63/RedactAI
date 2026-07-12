const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
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
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Only set Content-Type for non-FormData
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
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

  // ─── Auth ──────────────────────────────────────────────
  async login(email: string, password: string) {
    return this.request<{ access_token: string; refresh_token: string; token_type: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    );
  }

  async register(data: { email: string; password: string; full_name: string; organization_name?: string }) {
    return this.request<{ access_token: string; refresh_token: string; token_type: string }>(
      "/auth/register",
      { method: "POST", body: JSON.stringify(data) }
    );
  }

  async logout(refreshToken: string) {
    return this.request<{ message: string }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async refreshToken(refreshToken: string) {
    return this.request<{ access_token: string; refresh_token: string; token_type: string }>(
      "/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }
    );
  }

  // ─── Users ─────────────────────────────────────────────
  async getProfile() {
    return this.request<any>("/users/me");
  }

  async updateProfile(data: { full_name?: string; avatar_url?: string }) {
    return this.request<any>("/users/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async changePassword(data: { current_password: string; new_password: string }) {
    return this.request<{ message: string }>("/users/me/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ─── Organizations ────────────────────────────────────
  async getOrganizations() {
    return this.request<{ organizations: any[]; total: number }>("/organizations");
  }

  async createOrganization(data: any) {
    return this.request<any>("/organizations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ─── Documents ────────────────────────────────────────
  async uploadDocument(file: File, title: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);

    return this.request<{ document: any; message: string }>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getDocuments(params?: {
    search?: string;
    status?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }) {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          queryParams.append(key, String(value));
        }
      });
    }
    const query = queryParams.toString();
    return this.request<any>(`/documents${query ? `?${query}` : ""}`);
  }

  async getDocument(id: string) {
    return this.request<any>(`/documents/${id}`);
  }

  async deleteDocument(id: string) {
    return this.request<{ message: string }>(`/documents/${id}`, { method: "DELETE" });
  }

  async getDashboard() {
    return this.request<{ stats: any; recent_activity: any[] }>("/documents/dashboard");
  }

  // ─── Machine Learning ──────────────────────────────────────────
  async trainModel(datasetSize: number = 5000) {
    return this.request<any>("/ml/train", {
      method: "POST",
      body: JSON.stringify({ dataset_size: datasetSize }),
    });
  }

  async predictDocument(id: string) {
    return this.request<any>(`/ml/predict/${id}`, {
      method: "POST",
    });
  }

  async getMLModels() {
    return this.request<any[]>("/ml/models");
  }

  async getMLEvaluation() {
    return this.request<any>("/ml/evaluation");
  }

  async getMLExperiments(limit: number = 10) {
    return this.request<any[]>(`/ml/experiments?limit=${limit}`);
  }

  // ─── Deep Learning ─────────────────────────────────────────────
  async trainDLModel(epochs: number = 3, batchSize: number = 8, lr: number = 2e-5, datasetSize: number = 5000) {
    return this.request<any>("/dl/train", {
      method: "POST",
      body: JSON.stringify({ epochs, batch_size: batchSize, learning_rate: lr, dataset_size: datasetSize }),
    });
  }

  async predictDLDocument(id: string) {
    return this.request<any>(`/dl/predict/${id}`, {
      method: "POST",
    });
  }

  async getDLModels() {
    return this.request<any[]>("/dl/models");
  }

  async getDLEvaluation() {
    return this.request<any>("/dl/evaluation");
  }

  async getDLComparison() {
    return this.request<any>("/dl/comparison");
  }

  // ─── Validation ─────────────────────────────────────────────
  async getValidationReport() {
    return this.request<any>("/dl/validation-report");
  }

  // ─── Legal AI (Level 3) ──────────────────────────────────────
  async getLegalKnowledge(version: string = "v1.0.0") {
    return this.request<any>(`/legal/knowledge?version=${version}`);
  }

  async getLegalModels() {
    return this.request<any>("/legal/models");
  }

  async legalChat(documentId: string, question: string, kbVersion: string = "v1.0.0") {
    return this.request<any>("/legal/chat", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, question, kb_version: kbVersion })
    });
  }

  async analyzeLegalDocument(documentId: string) {
    return this.request<any>(`/legal/analyze/${documentId}`, { method: "POST" });
  }

  async checkCompliance(documentId: string) {
    return this.request<any>(`/legal/compliance/${documentId}`, { method: "POST" });
  }

  async summarizeLegalDocument(documentId: string) {
    return this.request<any>(`/legal/summarize/${documentId}`, { method: "POST" });
  }

  async submitHumanReview(data: {
    document_id: string;
    category: string;
    ai_recommendation: any;
    reviewer_decision: string;
    reviewer_comments?: string;
    final_decision: any;
  }) {
    return this.request<any>("/legal/review", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async getAIQualityMetrics() {
    return this.request<any>("/legal/quality");
  }

  async runAIQualityBenchmark(useSlm: boolean = false) {
    return this.request<any>(`/legal/benchmark?use_slm=${useSlm}`, { method: "POST" });
  }

  async getVersionedPrompts(promptId: string = "rag_qa_template") {
    return this.request<any>(`/legal/prompts?prompt_id=${promptId}`);
  }

  async registerPrompt(data: {
    prompt_id: string;
    version: string;
    template: string;
    associated_model: string;
    kb_version: string;
    metrics?: any;
  }) {
    return this.request<any>("/legal/prompts/register", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  // ─── Performance Optimization & Queue Monitoring ──────────────
  async getPerformanceStats() {
    return this.request<any>("/legal/performance");
  }

  async runPerformanceBenchmark(concurrency: number = 10) {
    return this.request<any>(`/legal/performance/benchmark?concurrency=${concurrency}`, { method: "POST" });
  }

  async getHistoricalBenchmarks() {
    return this.request<any>("/legal/performance/benchmarks");
  }
}

export const apiClient = new ApiClient();
