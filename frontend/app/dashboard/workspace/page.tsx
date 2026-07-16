"use client";

import React, { useState, useEffect } from "react";
import { copilotService } from "@/services/copilot";
import {
  Bookmark, Trash2, Search, Sparkles, FileText, Calendar, ShieldCheck, HelpCircle, ArrowRight
} from "lucide-react";
import Link from "next/link";

interface WorkspaceItem {
  id: string;
  item_type: string;
  title: string;
  content: string;
  metadata_json?: {
    source_document?: string;
    citations?: any[];
  };
  created_at: string;
}

export default function WorkspacePage() {
  const [items, setItems] = useState<WorkspaceItem[]>([]);
  const [selectedType, setSelectedType] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const loadItems = async () => {
    try {
      setLoading(true);
      const res = await copilotService.getWorkspaceItems(selectedType || undefined);
      setItems(res);
    } catch (err) {
      console.error("Failed to load workspace items", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, [selectedType]);

  const handleDeleteItem = async (id: string) => {
    if (!confirm("Are you sure you want to remove this saved item from your workspace?")) return;
    try {
      await copilotService.deleteWorkspaceItem(id);
      loadItems();
    } catch (err) {
      console.error("Failed to delete workspace item", err);
    }
  };

  // Filter items by search query
  const filteredItems = items.filter((item) => {
    const titleMatch = item.title.toLowerCase().includes(searchQuery.toLowerCase());
    const contentMatch = item.content.toLowerCase().includes(searchQuery.toLowerCase());
    const docMatch = item.metadata_json?.source_document?.toLowerCase().includes(searchQuery.toLowerCase()) || false;
    return titleMatch || contentMatch || docMatch;
  });

  const getItemTypeBadge = (type: string) => {
    switch (type) {
      case "pinned_clause":
        return { label: "Clause", bg: "bg-blue-500/10 text-blue-400 border-blue-500/25", icon: Bookmark };
      case "obligation":
        return { label: "Obligation", bg: "bg-purple-500/10 text-purple-400 border-purple-500/25", icon: ShieldCheck };
      case "summary":
        return { label: "Summary", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25", icon: FileText };
      default:
        return { label: "General", bg: "bg-slate-500/10 text-slate-400 border-slate-500/25", icon: HelpCircle };
    }
  };

  return (
    <div className="min-h-[80vh] text-slate-100 font-sans space-y-8 animate-fade-in">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.06] pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="p-2 bg-brand-500/15 rounded-xl border border-brand-500/25 text-brand-400">
              <Bookmark className="w-5 h-5" />
            </span>
            AI Legal Workspace
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Browse and manage your pinned clauses, compliance assessments, and extracted obligations.
          </p>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        {/* Search */}
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search saved clauses, content, or documents..."
            className="w-full bg-slate-900/40 border border-white/[0.06] rounded-xl pl-9 pr-4 py-3 text-xs text-slate-200 focus:outline-none focus:border-brand-500 transition"
          />
        </div>

        {/* Category Tabs */}
        <div className="flex gap-2">
          {[
            { label: "All Items", val: "" },
            { label: "Clauses", val: "pinned_clause" },
            { label: "Obligations", val: "obligation" },
            { label: "Summaries", val: "summary" }
          ].map((tab) => (
            <button
              key={tab.val}
              onClick={() => setSelectedType(tab.val)}
              className={`px-4 py-2 text-xs font-semibold rounded-xl transition ${
                selectedType === tab.val
                  ? "bg-brand-500 text-white"
                  : "bg-slate-900/40 border border-white/[0.06] text-slate-400 hover:bg-white/[0.02]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-slate-900/20 border border-white/[0.04] p-6 rounded-2xl h-48 animate-pulse"></div>
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-20 bg-slate-900/10 border border-white/[0.04] rounded-2xl">
          <Bookmark className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <h3 className="text-sm font-bold text-slate-400">No saved items found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Pin responses during Copilot consultations to keep them handy here in your workspace.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredItems.map((item) => {
            const badge = getItemTypeBadge(item.item_type);
            return (
              <div
                key={item.id}
                className="bg-slate-900/20 border border-white/[0.05] hover:border-brand-500/20 rounded-2xl p-5 flex flex-col justify-between transition group shadow-md"
              >
                <div className="space-y-4">
                  {/* Card Header */}
                  <div className="flex justify-between items-start gap-3">
                    <span className={`px-2 py-0.5 text-[9px] font-bold tracking-wider uppercase rounded border flex items-center gap-1 ${badge.bg}`}>
                      <badge.icon className="w-2.5 h-2.5" /> {badge.label}
                    </span>
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 text-slate-500 rounded transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Card Body */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold text-slate-200 leading-snug">{item.title}</h3>
                    <p className="text-[11px] text-[#AEB6C4] line-clamp-4 leading-relaxed whitespace-pre-wrap">
                      {item.content}
                    </p>
                  </div>
                </div>

                {/* Card Footer */}
                {item.metadata_json && (
                  <div className="mt-4 pt-4 border-t border-white/[0.04] flex justify-between items-center text-[10px] text-slate-500 font-mono">
                    <span className="truncate max-w-[150px]">
                      📄 {item.metadata_json.source_document || "General Guide"}
                    </span>
                    {item.metadata_json.citations && item.metadata_json.citations.length > 0 && (
                      <Link
                        href={`/dashboard/documents/${item.metadata_json.citations[0].document_id}?page=${item.metadata_json.citations[0].page_number}`}
                        className="text-brand-400 hover:text-white flex items-center gap-1 transition"
                      >
                        View Original <ArrowRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
