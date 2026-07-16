"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/services/api";

interface RAGStats {
  indexed_documents: number;
  total_chunks: number;
  total_vectors: number;
  avg_latency_ms: number;
  growth_history: Array<{ date: string; count: number }>;
  most_asked_questions: string[];
  top_retrieved_documents: Array<{ title: string; retrievals: number }>;
}

interface Citation {
  citation: string;
  is_hallucinated: boolean;
  document_name: string;
  page_number: number;
  section: string;
  confidence: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  confidenceScore?: number;
  confidenceReason?: string;
  citations?: Citation[];
  warning?: string;
  inferenceTimeMs?: number;
  reasoningEngine?: string;
}

export default function RAGDashboardPage() {
  const [stats, setStats] = useState<RAGStats | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [loadingStats, setLoadingStats] = useState(true);

  // Configuration form fields
  const [chunkStrategy, setChunkStrategy] = useState("paragraph");
  const [embeddingModel, setEmbeddingModel] = useState("MiniLM");
  const [indexingDocId, setIndexingDocId] = useState("");
  const [indexingStatus, setIndexingStatus] = useState("");
  const [reindexingModel, setReindexingModel] = useState("MiniLM");
  const [reindexingStatus, setReindexingStatus] = useState("");

  const loadData = async () => {
    try {
      setLoadingStats(true);
      const [statsRes, docsRes] = await Promise.all([
        apiClient.getRAGStatistics(),
        apiClient.getRAGDocuments(),
      ]);
      setStats(statsRes);
      setDocuments(docsRes);
      if (docsRes.length > 0 && !selectedDocId) {
        setSelectedDocId(""); // default to global search
      }
    } catch (err) {
      console.error("Failed to load RAG statistics/documents", err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage: ChatMessage = { role: "user", text: query };
    setChatHistory((prev) => [...prev, userMessage]);
    setLoadingQuery(true);
    const originalQuery = query;
    setQuery("");

    try {
      const res = await apiClient.queryRAG(
        originalQuery,
        selectedDocId || undefined,
        undefined
      );
      const assistantMessage: ChatMessage = {
        role: "assistant",
        text: res.answer,
        confidenceScore: res.confidence_score,
        confidenceReason: res.confidence_reason,
        citations: res.citations,
        warning: res.warning,
        inferenceTimeMs: res.inference_time_ms,
        reasoningEngine: res.reasoning_engine,
      };
      setChatHistory((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Error executing query: ${err.message || err}`,
        },
      ]);
    } finally {
      setLoadingQuery(false);
      loadData();
    }
  };

  const handleIndexDocument = async () => {
    if (!indexingDocId) {
      setIndexingStatus("Please select a document ID to index");
      return;
    }
    setIndexingStatus("Indexing started...");
    try {
      const res = await apiClient.indexDocumentRAG(
        indexingDocId,
        chunkStrategy,
        embeddingModel
      );
      setIndexingStatus(`Successfully indexed ${res.chunks_count} chunks!`);
      loadData();
    } catch (err: any) {
      setIndexingStatus(`Error: ${err.message || err}`);
    }
  };

  const handleReindexAll = async () => {
    setReindexingStatus("Batch re-indexing started...");
    try {
      const res = await apiClient.reindexRAG(reindexingModel);
      setReindexingStatus(`Reindexed ${res.affected_chunks} chunks successfully!`);
      loadData();
    } catch (err: any) {
      setReindexingStatus(`Error: ${err.message || err}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <span className="p-2 bg-indigo-600 rounded-lg text-white text-xl">RAG</span>
            Enterprise Knowledge Intelligence Dashboard
          </h1>
          <p className="text-slate-400 mt-2">
            Grounded Q&A, multi-model embedding pipelines, and semantic citations lookup.
          </p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-200 rounded-lg text-sm font-medium transition duration-200"
        >
          Refresh Stats
        </button>
      </div>

      {/* Metrics Grid */}
      {loadingStats ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-slate-900/50 border border-slate-850 p-6 rounded-xl animate-pulse h-28"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden shadow-lg transition transform hover:-translate-y-0.5">
            <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Indexed Documents</div>
            <div className="text-3xl font-black mt-2 text-white">{stats?.indexed_documents || 0}</div>
            <div className="absolute right-4 bottom-4 text-slate-800 font-extrabold text-5xl select-none">DOC</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden shadow-lg transition transform hover:-translate-y-0.5">
            <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Total Active Chunks</div>
            <div className="text-3xl font-black mt-2 text-indigo-400">{stats?.total_chunks || 0}</div>
            <div className="absolute right-4 bottom-4 text-slate-800 font-extrabold text-5xl select-none">CHNK</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden shadow-lg transition transform hover:-translate-y-0.5">
            <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Total Dense Vectors</div>
            <div className="text-3xl font-black mt-2 text-emerald-400">{stats?.total_vectors || 0}</div>
            <div className="absolute right-4 bottom-4 text-slate-800 font-extrabold text-5xl select-none">VEC</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl relative overflow-hidden shadow-lg transition transform hover:-translate-y-0.5">
            <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Avg Latency (Query)</div>
            <div className="text-3xl font-black mt-2 text-rose-400">
              {stats?.avg_latency_ms ? `${stats.avg_latency_ms} ms` : "0.0 ms"}
            </div>
            <div className="absolute right-4 bottom-4 text-slate-800 font-extrabold text-5xl select-none">TIME</div>
          </div>
        </div>
      )}

      {/* Main Panel Content: Left Side controls & Q&A, Right Side configurations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Grounded Q&A Interface Panel (Span 2) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex flex-col min-h-[500px]">
            <div className="flex justify-between items-center mb-4 border-b border-slate-850 pb-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></span>
                Grounded Legal Q&A Assistant
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-slate-400 text-xs font-medium">Search Scope:</label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="">Global (All Indexed Docs)</option>
                  {documents.map((doc) => (
                    <option key={doc.document_id} value={doc.document_id}>
                      {doc.title} ({doc.chunks_count} chunks)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Chat message logs */}
            <div className="flex-1 overflow-y-auto max-h-[350px] mb-4 space-y-4 pr-2">
              {chatHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center text-center h-full py-16">
                  <div className="text-slate-700 text-6xl mb-4">💬</div>
                  <h3 className="text-slate-400 font-semibold text-lg">No active conversation</h3>
                  <p className="text-slate-500 text-sm max-w-sm mt-1">
                    Ask questions about DPDP obligations, RBI guidelines, or compliance parameters in your documents.
                  </p>
                </div>
              ) : (
                chatHistory.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col max-w-[90%] ${
                      msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"
                    }`}
                  >
                    <div
                      className={`p-4 rounded-xl text-sm leading-relaxed shadow ${
                        msg.role === "user"
                          ? "bg-indigo-600 text-white rounded-br-none"
                          : "bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none"
                      }`}
                    >
                      {msg.text}
                    </div>

                    {/* Metadata details for Assistant generated response */}
                    {msg.role === "assistant" && (
                      <div className="mt-2 w-full space-y-2">
                        {/* Warnings banner */}
                        {msg.warning && (
                          <div className="p-2.5 bg-rose-950/40 border border-rose-900 text-rose-300 text-xs rounded-lg">
                            ⚠️ {msg.warning}
                          </div>
                        )}

                        <div className="flex flex-wrap gap-2 text-[10px] text-slate-500 font-mono">
                          {msg.reasoningEngine && <span>Engine: {msg.reasoningEngine}</span>}
                          {msg.inferenceTimeMs && <span>Latency: {msg.inferenceTimeMs}ms</span>}
                          {msg.confidenceScore !== undefined && (
                            <span
                              className={`font-semibold ${
                                msg.confidenceScore >= 0.85
                                  ? "text-emerald-400"
                                  : msg.confidenceScore >= 0.65
                                  ? "text-amber-400"
                                  : "text-rose-400"
                              }`}
                            >
                              Confidence: {(msg.confidenceScore * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>

                        {/* Citation Markers */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="bg-slate-950 border border-slate-900 rounded-lg p-3">
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                              Source Citations:
                            </div>
                            <div className="space-y-1">
                              {msg.citations.map((cit, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="text-xs flex items-center justify-between p-1 bg-slate-900/60 rounded border border-slate-850"
                                >
                                  <span className="text-slate-300">
                                    📄 {cit.document_name} (Page {cit.page_number})
                                  </span>
                                  <span className="text-slate-500 italic text-[11px]">
                                    {cit.section} (Match: {(cit.confidence * 100).toFixed(0)}%)
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* User Query Form */}
            <form onSubmit={handleSendQuery} className="flex gap-3 border-t border-slate-850 pt-4">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a legal compliance question..."
                className="flex-1 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                disabled={loadingQuery}
              />
              <button
                type="submit"
                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 text-white rounded-lg text-sm font-semibold transition"
                disabled={loadingQuery}
              >
                {loadingQuery ? "Answering..." : "Ask AI"}
              </button>
            </form>
          </div>
        </div>

        {/* Configurations Side Panel (Span 1) */}
        <div className="flex flex-col gap-6">
          {/* Indexing Configuration Box */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-bold text-white mb-4 border-b border-slate-850 pb-3 flex items-center gap-2">
              🔧 Index Document Configs
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-2">Target Document</label>
                <select
                  value={indexingDocId}
                  onChange={(e) => setIndexingDocId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-sm rounded-lg p-2.5 focus:outline-none"
                >
                  <option value="">Select Document to Index...</option>
                  {documents.map((doc) => (
                    <option key={doc.document_id} value={doc.document_id}>
                      {doc.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-2">Chunk strategy</label>
                <div className="grid grid-cols-3 gap-2">
                  {["paragraph", "clause", "section"].map((strat) => (
                    <button
                      key={strat}
                      onClick={() => setChunkStrategy(strat)}
                      className={`py-1.5 px-2 text-xs font-medium rounded-lg border transition ${
                        chunkStrategy === strat
                          ? "bg-indigo-600 border-indigo-500 text-white"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-900"
                      }`}
                    >
                      {strat.charAt(0).toUpperCase() + strat.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-2">Embedding Provider</label>
                <select
                  value={embeddingModel}
                  onChange={(e) => setEmbeddingModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-sm rounded-lg p-2.5 focus:outline-none"
                >
                  <option value="MiniLM">MiniLM (384 Dimensions)</option>
                  <option value="LegalBERT">LegalBERT (768 Dimensions)</option>
                  <option value="BGE">BGE (384 Dimensions)</option>
                </select>
              </div>

              <button
                onClick={handleIndexDocument}
                className="w-full py-2.5 bg-slate-950 hover:bg-slate-850 border border-slate-850 hover:border-slate-700 text-indigo-400 font-semibold rounded-lg text-sm transition"
              >
                Trigger Ingestion Pipeline
              </button>

              {indexingStatus && (
                <div className="p-3 bg-slate-950 text-xs rounded border border-slate-850 text-center font-mono">
                  {indexingStatus}
                </div>
              )}
            </div>
          </div>

          {/* Re-indexing Configuration Box */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-bold text-white mb-4 border-b border-slate-850 pb-3 flex items-center gap-2">
              🔄 Batch Reindexing Engine
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-2">Target Embedding Provider</label>
                <select
                  value={reindexingModel}
                  onChange={(e) => setReindexingModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-sm rounded-lg p-2.5 focus:outline-none"
                >
                  <option value="MiniLM">MiniLM (384 Dimensions)</option>
                  <option value="LegalBERT">LegalBERT (768 Dimensions)</option>
                  <option value="BGE">BGE (384 Dimensions)</option>
                </select>
              </div>

              <button
                onClick={handleReindexAll}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm transition"
              >
                Re-index Knowledge Base
              </button>

              {reindexingStatus && (
                <div className="p-3 bg-slate-950 text-xs rounded border border-slate-850 text-center font-mono">
                  {reindexingStatus}
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
