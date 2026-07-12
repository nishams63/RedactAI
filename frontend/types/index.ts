// ─── Auth Types ──────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  organization_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ─── User Types ──────────────────────────────────────────
export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  organization_id: string | null;
  organization_name: string | null;
  roles: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UpdateProfileRequest {
  full_name?: string;
  avatar_url?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ─── Organization Types ──────────────────────────────────
export interface Organization {
  id: string;
  name: string;
  logo_url: string | null;
  address: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationListResponse {
  organizations: Organization[];
  total: number;
}

// ─── Document Types ──────────────────────────────────────
export interface Document {
  id: string;
  title: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  owner_id: string;
  organization_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Dashboard Types ─────────────────────────────────────
export interface DashboardStats {
  total_documents: number;
  documents_processed: number;
  pending_documents: number;
  failed_documents: number;
  total_users: number;
}

export interface RecentActivity {
  id: string;
  title: string;
  action: string;
  timestamp: string;
}

export interface DashboardResponse {
  stats: DashboardStats;
  recent_activity: RecentActivity[];
}

// ─── API Response ────────────────────────────────────────
export interface MessageResponse {
  message: string;
}

export interface ApiError {
  detail: string;
}
