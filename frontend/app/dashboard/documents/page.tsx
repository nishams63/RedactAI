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
      window.open(`http://localhost:8000/api/v1/documents/local-preview/${cleanPath}`, "_blank");
    } else {
      alert("Preview is only available for locally stored fallback files in Sprint 1.");
    }
  };

  const documents = data?.documents || [];
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Documents</h1>
          <p className="text-[rgb(var(--text-secondary))] mt-1">
            Manage and process your legal documents
          </p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn-primary shrink-0">
          <Upload className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* Search and Filters */}
      <div className="glass-card p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[rgb(var(--text-secondary))]" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="input-field pl-12"
              placeholder="Search by title or filename..."
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[rgb(var(--text-secondary))]" />
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

      {/* Documents Table */}
      <div
        className="glass-card overflow-hidden"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isDragging && (
          <div className="absolute inset-0 z-10 bg-brand-500/10 border-2 border-dashed border-brand-500 rounded-2xl flex items-center justify-center backdrop-blur-sm">
            <div className="text-center">
              <CloudUpload className="w-12 h-12 text-brand-500 mx-auto mb-2" />
              <p className="text-brand-500 font-semibold">Drop file to upload</p>
            </div>
          </div>
        )}

        {/* Table Header */}
        <div className="hidden md:grid grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-4 px-6 py-4 bg-[rgb(var(--bg-secondary))]/50 text-xs font-semibold uppercase tracking-wider text-[rgb(var(--text-secondary))]">
          <button onClick={() => toggleSort("title")} className="flex items-center gap-1 hover:text-[rgb(var(--text-primary))] transition-colors">
            Document {sortBy === "title" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <span>Size</span>
          <span>Type</span>
          <button onClick={() => toggleSort("status")} className="flex items-center gap-1 hover:text-[rgb(var(--text-primary))] transition-colors">
            Status {sortBy === "status" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <button onClick={() => toggleSort("created_at")} className="flex items-center gap-1 hover:text-[rgb(var(--text-primary))] transition-colors">
            Date {sortBy === "created_at" && (sortOrder === "asc" ? <SortAsc className="w-3 h-3" /> : <SortDesc className="w-3 h-3" />)}
          </button>
          <span>Actions</span>
        </div>

        {/* Table Body */}
        {isLoading ? (
          <div className="divide-y divide-[rgb(var(--border-color))]/50">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-6 py-4 grid grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-4">
                {[...Array(6)].map((_, j) => (
                  <div key={j} className="h-5 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
                ))}
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-16 h-16 mx-auto text-[rgb(var(--text-secondary))]/30 mb-4" />
            <p className="text-lg font-semibold mb-2">No documents found</p>
            <p className="text-[rgb(var(--text-secondary))] text-sm mb-6">Upload your first document to get started</p>
            <button onClick={() => setShowUpload(true)} className="btn-primary">
              <Upload className="w-4 h-4" /> Upload Document
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[rgb(var(--border-color))]/50">
            {documents.map((doc: any) => {
              const IconComponent = mimeIcons[doc.mime_type] || File;
              return (
                <div key={doc.id} className="table-row px-6 py-4 grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr_1fr_1fr_80px] gap-2 md:gap-4 items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-brand-500/10 rounded-xl flex items-center justify-center shrink-0">
                      <IconComponent className="w-5 h-5 text-brand-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate">{doc.title}</p>
                      <p className="text-xs text-[rgb(var(--text-secondary))] truncate">{doc.original_filename}</p>
                    </div>
                  </div>
                  <span className="text-sm text-[rgb(var(--text-secondary))]">{formatBytes(doc.file_size)}</span>
                  <span className="text-sm text-[rgb(var(--text-secondary))]">
                    {doc.mime_type?.split("/").pop()?.toUpperCase() || "—"}
                  </span>
                  <span className={statusColors[doc.status] || "badge-info"}>
                    {doc.status}
                  </span>
                  <span className="text-sm text-[rgb(var(--text-secondary))]">{formatDate(doc.created_at)}</span>
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => handlePreview(doc)}
                      className="w-8 h-8 rounded-lg hover:bg-[rgb(var(--bg-secondary))] flex items-center justify-center text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))] transition-colors"
                      title="Preview"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => { if (confirm("Delete this document?")) deleteMutation.mutate(doc.id); }}
                      className="w-8 h-8 rounded-lg hover:bg-red-500/10 flex items-center justify-center text-[rgb(var(--text-secondary))] hover:text-red-500 transition-colors"
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
          <div className="flex items-center justify-between px-6 py-4 border-t border-[rgb(var(--border-color))]/50">
            <p className="text-sm text-[rgb(var(--text-secondary))]">
              Page {page} of {totalPages} ({data?.total || 0} documents)
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="btn-secondary !px-3 !py-2 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="btn-secondary !px-3 !py-2 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowUpload(false)} />
          <div className="relative glass-card w-full max-w-lg p-8 animate-slide-up">
            <button
              onClick={() => setShowUpload(false)}
              className="absolute top-4 right-4 w-8 h-8 rounded-lg hover:bg-[rgb(var(--bg-secondary))] flex items-center justify-center text-[rgb(var(--text-secondary))]"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-2xl font-bold mb-6">Upload Document</h2>

            <form onSubmit={handleUploadSubmit} className="space-y-5">
              {/* Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                  ${uploadFile
                    ? "border-brand-500/50 bg-brand-500/5"
                    : "border-[rgb(var(--border-color))] hover:border-brand-500/30 hover:bg-brand-500/5"
                  }`}
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
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="w-10 h-10 text-brand-500" />
                    <p className="text-sm font-semibold">{uploadFile.name}</p>
                    <p className="text-xs text-[rgb(var(--text-secondary))]">{formatBytes(uploadFile.size)}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <CloudUpload className="w-10 h-10 text-[rgb(var(--text-secondary))]/50" />
                    <p className="text-sm font-medium">Drop file here or click to browse</p>
                    <p className="text-xs text-[rgb(var(--text-secondary))]">PDF, DOCX, PNG, JPEG, TIFF — Max 50 MB</p>
                  </div>
                )}
              </div>

              {/* Title */}
              <div>
                <label htmlFor="docTitle" className="block text-sm font-semibold mb-2">Document Title</label>
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
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <><Upload className="w-4 h-4" /> Upload Document</>
                )}
              </button>

              {uploadMutation.isError && (
                <p className="text-sm text-red-500 text-center">
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
