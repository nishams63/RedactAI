"use client";

import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatBytes, formatDate } from "@/lib/utils";
import {
  Upload, Search, Filter, FileText, Trash2, Eye, X,
  ChevronLeft, ChevronRight, SortAsc, SortDesc, CloudUpload,
  File, Image as ImageIcon, FileType,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const statusColors: Record<string, string> = {
  Pending: "badge-warning",
  Processed: "badge-success",
  Failed: "badge-danger",
};

const mimeIcons: Record<string, typeof FileText> = {
  "application/pdf": FileText,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType,
  "image/png": ImageIcon,
  "image/jpeg": ImageIcon,
};

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["documents", search, statusFilter, sortBy, sortOrder, page],
    queryFn: () =>
      apiClient.getDocuments({
        search: search || undefined,
        status: statusFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: 15,
      }),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) =>
      apiClient.uploadDocument(file, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setShowUpload(false);
      setUploadFile(null);
      setUploadTitle("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error: any) => {
      alert(`Failed to delete document: ${error.message || "Unknown error"}`);
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setUploadFile(file);
      setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
      setShowUpload(true);
    }
  }, []);

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadFile && uploadTitle) {
      uploadMutation.mutate({ file: uploadFile, title: uploadTitle });
    }
  };

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  };

  const handlePreview = (doc: any) => {
    if (doc.storage_path && doc.storage_path.startsWith("local://")) {
      let cleanPath = doc.storage_path.replace("local://", "");
      if (doc.status === "Processed") {
        cleanPath = cleanPath.replace("uploads/", "redacted/");
      }
      const token = localStorage.getItem("access_token");
      const url = `${API_URL}/documents/local-preview/${cleanPath}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      window.open(url, "_blank");
    } else {
      alert("Preview is only available for locally stored fallback files in Sprint 1.");
    }
  };

  const documents = data?.documents || [];
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ── Header ───────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#AEB6C4]/40 mb-3">Document Vault</p>
          <h1 className="text-display text-4xl">Documents</h1>
          <p className="text-[#AEB6C4]/50 mt-2 text-sm font-light">
            Manage and process your legal documents
          </p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn-primary shrink-0">
          <Upload className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* ── Search & Filters ─────────────────────────────── */}
      <div className="glass-card p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#AEB6C4]/30" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="input-field pl-11"
              placeholder="Search by title or filename..."
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Filter className="w-3.5 h-3.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#AEB6C4]/30" />
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="input-field pl-10 pr-8 appearance-none cursor-pointer min-w-[140px]"
              >
                <option value="">All Status</option>
                <option value="Pending">Pending</option>
                <option value="Processed">Processed</option>
                <option value="Failed">Failed</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ── Documents Table ──────────────────────────────── */}
      <div
        className="glass-card overflow-hidden relative"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isDragging && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-[20px]"
               style={{ background: 'rgba(79,124,255,0.06)', border: '2px dashed rgba(79,124,255,0.3)', backdropFilter: 'blur(4px)' }}>
            <div className="text-center">
              <CloudUpload className="w-12 h-12 mx-auto mb-3" style={{ color: '#4F7CFF' }} />
              <p className="font-semibold text-brand-500">Drop file to upload</p>
            </div>
          </div>
        )}

        {/* Table Header */}
        <div className="hidden md:grid grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-4 px-7 py-4 text-[10px] font-semibold uppercase tracking-[0.15em]"
             style={{ color: 'rgba(174,182,196,0.35)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <button onClick={() => toggleSort("title")} className="flex items-center gap-1.5 hover:text-white transition-colors text-left">
            Document {sortBy === "title" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <span>Size</span>
          <span>Type</span>
          <button onClick={() => toggleSort("status")} className="flex items-center gap-1.5 hover:text-white transition-colors text-left">
            Status {sortBy === "status" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <button onClick={() => toggleSort("created_at")} className="flex items-center gap-1.5 hover:text-white transition-colors text-left">
            Date {sortBy === "created_at" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <span>Actions</span>
        </div>

        {/* Table Body */}
        {isLoading ? (
          <div>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-7 py-4 grid grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-4"
                   style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                {[...Array(6)].map((_, j) => (
                  <div key={j} className="h-5 rounded-lg animate-pulse" style={{ background: 'rgba(255,255,255,0.03)' }} />
                ))}
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center"
                 style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
              <FileText className="w-7 h-7 text-[#AEB6C4]/15" />
            </div>
            <p className="text-lg font-display font-semibold mb-2">No documents found</p>
            <p className="text-[#AEB6C4]/40 text-sm mb-8 font-light">Upload your first document to get started</p>
            <button onClick={() => setShowUpload(true)} className="btn-primary">
              <Upload className="w-4 h-4" /> Upload Document
            </button>
          </div>
        ) : (
          <div>
            {documents.map((doc: any) => {
              const IconComponent = mimeIcons[doc.mime_type] || File;
              return (
                <div key={doc.id} className="table-row px-7 py-4 grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-2 md:gap-4 items-center group">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                         style={{ background: 'rgba(79,124,255,0.06)', border: '1px solid rgba(79,124,255,0.08)' }}>
                      <IconComponent className="w-[18px] h-[18px] text-brand-500/70" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate group-hover:text-white transition-colors">{doc.title}</p>
                      <p className="text-xs text-[#AEB6C4]/30 truncate mt-0.5">{doc.original_filename}</p>
                    </div>
                  </div>
                  <span className="text-sm text-[#AEB6C4]/40 tabular-nums">{formatBytes(doc.file_size)}</span>
                  <span className="text-sm text-[#AEB6C4]/40 font-mono text-xs">
                    {doc.mime_type?.split("/").pop()?.toUpperCase() || "—"}
                  </span>
                  <span className={statusColors[doc.status] || "badge-info"}>
                    {doc.status}
                  </span>
                  <span className="text-sm text-[#AEB6C4]/30 tabular-nums">{formatDate(doc.created_at)}</span>
                  <div className="flex items-center gap-0.5">
                    <button
                      onClick={() => handlePreview(doc)}
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-[#AEB6C4]/30 hover:text-brand-500 hover:bg-brand-500/[0.06] transition-all duration-200"
                      title="Preview"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => { if (confirm("Delete this document?")) deleteMutation.mutate(doc.id); }}
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-[#AEB6C4]/30 hover:text-accent-danger hover:bg-[rgba(255,92,122,0.06)] transition-all duration-200"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-7 py-4"
               style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <p className="text-xs text-[#AEB6C4]/30 font-medium tabular-nums">
              Page {page} of {totalPages} ({data?.total || 0} documents)
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="btn-secondary !px-3 !py-2 disabled:opacity-20"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="btn-secondary !px-3 !py-2 disabled:opacity-20"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Upload Modal ─────────────────────────────────── */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0" style={{ background: 'rgba(9,11,18,0.85)', backdropFilter: 'blur(8px)' }}
               onClick={() => setShowUpload(false)} />
          <div className="relative glass-card w-full max-w-lg p-8 animate-slide-up" style={{ borderRadius: '24px' }}>
            <button
              onClick={() => setShowUpload(false)}
              className="absolute top-5 right-5 w-8 h-8 rounded-lg flex items-center justify-center text-[#AEB6C4]/30 hover:text-white hover:bg-white/[0.04] transition-all"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-display text-2xl mb-2">Upload Document</h2>
            <p className="text-[#AEB6C4]/40 text-sm mb-7 font-light">Add a new document for AI-powered analysis</p>

            <form onSubmit={handleUploadSubmit} className="space-y-6">
              {/* Drop Zone */}
              <div
                className={`rounded-2xl p-10 text-center cursor-pointer transition-all duration-300 ${
                  uploadFile ? "" : "hover:border-brand-500/30"
                }`}
                style={{
                  border: uploadFile ? '2px dashed rgba(79,124,255,0.3)' : '2px dashed rgba(255,255,255,0.06)',
                  background: uploadFile ? 'rgba(79,124,255,0.04)' : 'rgba(255,255,255,0.02)',
                }}
                onClick={() => document.getElementById("fileInput")?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files?.[0];
                  if (file) {
                    setUploadFile(file);
                    if (!uploadTitle) setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
                  }
                }}
              >
                <input
                  id="fileInput"
                  type="file"
                  accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setUploadFile(file);
                      if (!uploadTitle) setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
                    }
                  }}
                />
                {uploadFile ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                         style={{ background: 'rgba(79,124,255,0.1)', border: '1px solid rgba(79,124,255,0.15)' }}>
                      <FileText className="w-6 h-6 text-brand-500" />
                    </div>
                    <p className="text-sm font-semibold">{uploadFile.name}</p>
                    <p className="text-xs text-[#AEB6C4]/40">{formatBytes(uploadFile.size)}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                         style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
                      <CloudUpload className="w-6 h-6 text-[#AEB6C4]/20" />
                    </div>
                    <p className="text-sm font-medium">Drop file here or click to browse</p>
                    <p className="text-xs text-[#AEB6C4]/30">PDF, DOCX, PNG, JPEG, TIFF — Max 50 MB</p>
                  </div>
                )}
              </div>

              {/* Title */}
              <div>
                <label htmlFor="docTitle" className="block text-xs font-semibold mb-2.5 text-[#AEB6C4]/50 uppercase tracking-widest">
                  Document Title
                </label>
                <input
                  id="docTitle"
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="input-field"
                  placeholder="Enter document title"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={!uploadFile || !uploadTitle || uploadMutation.isPending}
                className="btn-primary w-full"
              >
                {uploadMutation.isPending ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <><Upload className="w-4 h-4" /> Upload Document</>
                )}
              </button>

              {uploadMutation.isError && (
                <p className="text-sm text-center" style={{ color: '#FF5C7A' }}>
                  {(uploadMutation.error as Error)?.message || "Upload failed"}
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
