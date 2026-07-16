"use client";

import React, { useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import {
  FileText, Shield, AlertOctagon, Info, ArrowLeft,
  ChevronLeft, ChevronRight, Activity, Terminal
} from "lucide-react";

// Color mappings for entity types
const ENTITY_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  // Critical
  AADHAAR: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", dot: "bg-red-500" },
  PASSPORT: { bg: "bg-red-600/10", border: "border-red-600/30", text: "text-red-300", dot: "bg-red-600" },
  BANK_ACCOUNT: { bg: "bg-red-700/10", border: "border-red-700/30", text: "text-red-200", dot: "bg-red-700" },
  // High
  PAN: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", dot: "bg-orange-500" },
  DRIVING_LICENSE: { bg: "bg-orange-400/10", border: "border-orange-400/30", text: "text-orange-300", dot: "bg-orange-400" },
  VOTER_ID: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", dot: "bg-amber-500" },
  CREDIT_CARD: { bg: "bg-amber-600/10", border: "border-amber-600/30", text: "text-amber-300", dot: "bg-amber-600" },
  // Medium
  PHONE: { bg: "bg-teal-500/10", border: "border-teal-500/30", text: "text-teal-400", dot: "bg-teal-500" },
  EMAIL: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", dot: "bg-emerald-500" },
  ADDRESS: { bg: "bg-indigo-500/10", border: "border-indigo-500/30", text: "text-indigo-400", dot: "bg-indigo-500" },
  // Low / NER
  PERSON: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", dot: "bg-blue-500" },
  ORGANIZATION: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", dot: "bg-purple-500" },
  LOCATION: { bg: "bg-sky-500/10", border: "border-sky-500/30", text: "text-sky-400", dot: "bg-sky-500" },
};

const RISK_BADGES: Record<string, string> = {
  CRITICAL: "badge-danger animate-pulse",
  HIGH: "badge-danger",
  MEDIUM: "badge-warning",
  LOW: "badge-success",
};

export default function DocumentViewerPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const searchParams = useSearchParams();
  const pageParam = searchParams ? searchParams.get("page") : null;
  const initialPage = pageParam ? parseInt(pageParam, 10) : 1;
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [activeTab, setActiveTab] = useState<"entities" | "logs">("entities");

  const { data: doc, isLoading, error } = useQuery({
    queryKey: ["document", id],
    queryFn: () => apiClient.getDocument(id),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-[rgb(var(--text-secondary))] animate-pulse">Running layouter & scanners...</p>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="glass-card p-8 text-center max-w-lg mx-auto mt-12">
        <AlertOctagon className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold mb-2">Error Loading Document</h2>
        <p className="text-[rgb(var(--text-secondary))] mb-6">{error?.message || "Document not found"}</p>
        <button onClick={() => router.push("/dashboard/documents")} className="btn-primary">
          <ArrowLeft className="w-4 h-4" /> Back to List
        </button>
      </div>
    );
  }

  const pages = doc.pages || [];
  const pageCount = doc.metadata?.page_count || pages.length || 1;
  const currentPageData = pages.find((p: any) => p.page_number === currentPage);
  const pageText = currentPageData?.text || "";

  // Filter entities by page
  const pageEntities = (doc.entities || []).filter((e: any) => e.page_number === currentPage);

  // Group entities for sidebar
  const entitiesByType = (doc.entities || []).reduce((acc: Record<string, any[]>, ent: any) => {
    acc[ent.entity_type] = acc[ent.entity_type] || [];
    acc[ent.entity_type].push(ent);
    return acc;
  }, {} as Record<string, any[]>);

  // Highlighting algorithm
  const renderHighlightedText = () => {
    if (pageEntities.length === 0) return pageText;

    const elements: React.ReactNode[] = [];
    let lastIdx = 0;

    // Sort page entities by start position
    const sorted = [...pageEntities].sort((a, b) => a.start_char - b.start_char);

    sorted.forEach((ent, idx) => {
      if (ent.start_char > lastIdx) {
        elements.push(pageText.slice(lastIdx, ent.start_char));
      }

      const colors = ENTITY_COLORS[ent.entity_type] || {
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/30",
        text: "text-yellow-400",
        dot: "bg-yellow-500",
      };

      elements.push(
        <span
          key={`${ent.id}-${idx}`}
          className={`inline-block border px-1.5 py-0.5 rounded cursor-pointer relative group transition-colors ${colors.bg} ${colors.border} ${colors.text}`}
        >
          {pageText.slice(ent.start_char, ent.end_char)}
          {/* Tooltip on Hover */}
          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 hidden group-hover:block z-30 p-2 bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))] rounded-lg shadow-xl text-xs text-[rgb(var(--text-primary))] leading-relaxed text-center pointer-events-none">
            <span className="block font-bold text-brand-400 mb-0.5">{ent.entity_type}</span>
            <span className="block text-[rgb(var(--text-secondary))] mb-0.5">
              Risk: <b className={ent.risk_level === "CRITICAL" || ent.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"}>{ent.risk_level}</b>
            </span>
            <span className="block text-[rgb(var(--text-secondary))]">
              Conf: <b>{Math.round(ent.confidence * 100)}%</b>
            </span>
          </span>
        </span>
      );

      lastIdx = ent.end_char;
    });

    if (lastIdx < pageText.length) {
      elements.push(pageText.slice(lastIdx));
    }

    return elements;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push("/dashboard/documents")} className="btn-secondary !p-3">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">{doc.title}</h1>
            <p className="text-xs text-[rgb(var(--text-secondary))] mt-0.5">
              File type: <span className="text-[rgb(var(--text-primary))] font-semibold">{doc.metadata?.file_type || "—"}</span> | Language: <span className="text-[rgb(var(--text-primary))] font-semibold">{doc.metadata?.language || "—"}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-[rgb(var(--text-secondary))] font-medium">Risk Profile:</span>
          <span className="badge-danger uppercase text-xs font-bold tracking-wide">
            {doc.entities?.some((e: any) => e.risk_level === "CRITICAL")
              ? "CRITICAL"
              : doc.entities?.some((e: any) => e.risk_level === "HIGH")
              ? "HIGH"
              : "MEDIUM"}
          </span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Document Panel */}
        <div className="xl:col-span-3 flex flex-col glass-card min-h-[70vh]">
          {/* Top Bar / Pagination */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[rgb(var(--border-color))]/50 bg-[rgb(var(--bg-secondary))]/30">
            <span className="text-sm font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4 text-brand-500" /> Page {currentPage} of {pageCount}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage <= 1}
                className="btn-secondary !p-2 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(pageCount, currentPage + 1))}
                disabled={currentPage >= pageCount}
                className="btn-secondary !p-2 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Text Area */}
          <div className="flex-1 p-8 overflow-y-auto max-h-[60vh] font-mono text-sm leading-relaxed whitespace-pre-wrap select-text">
            {currentPageData ? renderHighlightedText() : <p className="text-[rgb(var(--text-secondary))]/50 italic">No text extracted on this page.</p>}
          </div>
        </div>

        {/* Sidebar Info Panel */}
        <div className="glass-card flex flex-col max-h-[70vh]">
          {/* Tabs Header */}
          <div className="grid grid-cols-2 border-b border-[rgb(var(--border-color))]/50">
            <button
              onClick={() => setActiveTab("entities")}
              className={`py-3 text-sm font-bold border-b-2 transition-colors ${
                activeTab === "entities"
                  ? "border-brand-500 text-brand-500"
                  : "border-transparent text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
              }`}
            >
              Entities ({doc.entities?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab("logs")}
              className={`py-3 text-sm font-bold border-b-2 transition-colors ${
                activeTab === "logs"
                  ? "border-brand-500 text-brand-500"
                  : "border-transparent text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
              }`}
            >
              Pipeline Logs
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {activeTab === "entities" ? (
              Object.keys(entitiesByType).length === 0 ? (
                <div className="text-center py-12">
                  <Shield className="w-8 h-8 text-[rgb(var(--text-secondary))]/30 mx-auto mb-2" />
                  <p className="text-sm text-[rgb(var(--text-secondary))]">No entities detected</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(entitiesByType).map(([type, list]) => {
                    const listArray = list as any[];
                    const colors = ENTITY_COLORS[type] || { text: "text-brand-400", dot: "bg-brand-500" };
                    return (
                      <div key={type} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className={`text-xs font-bold tracking-wider uppercase flex items-center gap-1.5 ${colors.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} /> {type}
                          </span>
                          <span className="text-[10px] bg-[rgb(var(--bg-secondary))] px-2 py-0.5 rounded-full text-[rgb(var(--text-secondary))] font-bold">
                            {listArray.length}
                          </span>
                        </div>
                        <div className="space-y-1 pl-3 border-l border-[rgb(var(--border-color))]/50">
                          {listArray.map((ent: any) => (
                            <div key={ent.id} className="group relative flex justify-between text-xs p-1 hover:bg-[rgb(var(--bg-secondary))]/50 rounded transition-colors">
                              <span className="font-medium truncate max-w-[130px]" title={ent.value}>
                                {ent.value}
                              </span>
                              <span className="text-[10px] text-[rgb(var(--text-secondary))] font-semibold">
                                P.{ent.page_number} ({Math.round(ent.confidence * 100)}%)
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            ) : (
              <div className="space-y-3 font-mono text-[11px] leading-relaxed">
                {(doc.logs || []).length === 0 ? (
                  <div className="text-center py-12">
                    <Terminal className="w-8 h-8 text-[rgb(var(--text-secondary))]/30 mx-auto mb-2" />
                    <p className="text-sm text-[rgb(var(--text-secondary))]">No log entries found</p>
                  </div>
                ) : (
                  doc.logs.map((log: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded bg-[rgb(var(--bg-secondary))]/40 border border-[rgb(var(--border-color))]/30">
                      <div className="flex justify-between font-bold text-[10px] uppercase mb-1">
                        <span className={log.log_level === "ERROR" ? "text-red-400" : "text-brand-400"}>
                          [{log.stage}]
                        </span>
                        <span className="text-[rgb(var(--text-secondary))]">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-[rgb(var(--text-primary))]">{log.message}</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
