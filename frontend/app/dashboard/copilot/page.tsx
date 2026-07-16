"use client";

import React, { useState, useEffect, useRef } from "react";
import { copilotService } from "@/services/copilot";
import { apiClient } from "@/services/api";
import {
  MessageSquare, Bookmark, Send, Trash2, Search, Plus, Sparkles, AlertTriangle, Check, X, Edit3, ChevronDown, ChevronRight, FileText, Cpu, Clock, Layers, Star
} from "lucide-react";
import Link from "next/link";

interface Citation {
  document_id: string;
  document_name: string;
  page_number: number;
  section: string;
  clause: string;
  confidence: number;
}

interface Message {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  explainability?: {
    reasoning_summary?: string;
    model_used?: string;
    retrieval_latency_ms?: number;
    inference_time_ms?: number;
    total_latency_ms?: number;
    retrieved_chunk_ids?: string[];
    retrieved_document_ids?: string[];
  };
  needs_review?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  summary: string;
  document_ids: string[];
  created_at: string;
}

export default function CopilotPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [query, setQuery] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([
    "Explain notice obligations in my contracts.",
    "Do these terms comply with DPDP Section 4?",
    "Extract key obligations and timelines."
  ]);
  const [showReviewId, setShowReviewId] = useState<string | null>(null);
  const [reviewerComment, setReviewerComment] = useState("");
  const [editedText, setEditedText] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = async (search?: string) => {
    try {
      const res = await copilotService.getConversations({ search_query: search });
      setConversations(res);
    } catch (err) {
      console.error("Failed to load conversations", err);
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await apiClient.getDocuments();
      setDocuments(res.documents || []);
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  useEffect(() => {
    loadConversations();
    loadDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, isGenerating]);

  const selectConversation = async (id: string) => {
    try {
      setActiveConvId(id);
      const res = await copilotService.getConversationDetails(id);
      setMessages(res.messages || []);
      setSelectedDocIds(res.document_ids || []);
      
      if (res.messages && res.messages.length > 0) {
        setSuggestedQuestions([
          "Summarize the key timelines mentioned.",
          "Identify compliance exposure points.",
          "Explain the confidentiality clause."
        ]);
      }
    } catch (err) {
      console.error("Failed to load conversation details", err);
    }
  };

  const handleCreateNewConversation = () => {
    setActiveConvId(null);
    setMessages([]);
    setSelectedDocIds([]);
    setSuggestedQuestions([
      "Explain notice obligations in my contracts.",
      "Do these terms comply with DPDP Section 4?",
      "Extract key obligations and timelines."
    ]);
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this session?")) return;
    try {
      await copilotService.deleteConversation(id);
      if (activeConvId === id) {
        handleCreateNewConversation();
      }
      loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation", err);
    }
  };

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || isGenerating) return;

    const userMsg: Message = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setIsGenerating(true);
    setStreamingText("");

    try {
      const response = await copilotService.chatStream({
        message: textToSend,
        conversation_id: activeConvId || undefined,
        document_ids: selectedDocIds
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No readable stream reader found.");

      let currentCitations: Citation[] = [];
      let currentExplainability: any = {};
      let needsReview = false;
      let finalContent = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("event: token")) {
            const dataStr = line.slice("event: token\ndata: ".length).trim();
            try {
              const data = JSON.parse(dataStr);
              finalContent += data.text;
              setStreamingText((prev) => prev + data.text);
            } catch {}
          } else if (line.startsWith("event: citations")) {
            const dataStr = line.slice("event: citations\ndata: ".length).trim();
            try {
              const data = JSON.parse(dataStr);
              currentCitations = data.citations || [];
            } catch {}
          } else if (line.startsWith("event: completed")) {
            const dataStr = line.slice("event: completed\ndata: ".length).trim();
            try {
              const data = JSON.parse(dataStr);
              finalContent = data.answer;
              currentCitations = data.citations || [];
              currentExplainability = data.explainability || {};
              needsReview = data.needs_review || false;
            } catch {}
          } else if (line.startsWith("event: end")) {
            const dataStr = line.slice("event: end\ndata: ".length).trim();
            try {
              const data = JSON.parse(dataStr);
              if (!activeConvId) {
                setActiveConvId(data.conversation_id);
              }
            } catch {}
          }
        }
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: finalContent || streamingText,
        citations: currentCitations,
        explainability: currentExplainability,
        needs_review: needsReview
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreamingText("");
      setIsGenerating(false);
      loadConversations();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message || err}` }
      ]);
      setIsGenerating(false);
    }
  };

  const handleBookmark = async (msg: Message) => {
    try {
      const sourceDoc = msg.citations && msg.citations.length > 0 ? msg.citations[0].document_name : "General Guidance";
      await copilotService.pinWorkspaceItem({
        item_type: "pinned_clause",
        title: `Saved response from Copilot`,
        content: msg.content,
        metadata_json: {
          source_document: sourceDoc,
          citations: msg.citations
        }
      });
      alert("Obligation details bookmarked to AI Workspace successfully!");
    } catch (err) {
      console.error("Failed to pin item", err);
    }
  };

  const submitReview = async (msgIndex: number, decision: "APPROVED" | "EDITED" | "REJECTED") => {
    const msg = messages[msgIndex];
    if (!msg || !msg.id) return;
    try {
      await copilotService.submitHumanReview(msg.id, {
        reviewer_decision: decision,
        edited_answer: decision === "EDITED" ? editedText : undefined,
        reviewer_comments: reviewerComment
      });
      alert("Feedback saved successfully.");
      
      const updated = [...messages];
      updated[msgIndex] = {
        ...msg,
        content: decision === "EDITED" ? editedText : msg.content,
        needs_review: false
      };
      setMessages(updated);
      setShowReviewId(null);
      setReviewerComment("");
      setEditedText("");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[82vh] text-slate-100 font-sans">
      {/* ── Sidebar Conversations Panel ── */}
      <div className="w-full lg:w-80 bg-slate-900/40 border border-white/[0.05] rounded-2xl flex flex-col p-4 backdrop-blur-xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-md font-bold tracking-wider uppercase text-[#AEB6C4] flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-brand-500" /> Chats
          </h2>
          <button
            onClick={handleCreateNewConversation}
            className="p-2 bg-brand-500/10 border border-brand-500/20 hover:bg-brand-500 hover:text-white transition rounded-xl text-brand-400"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="relative mb-4">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              loadConversations(e.target.value);
            }}
            placeholder="Search discussions..."
            className="w-full bg-[#090B12] border border-white/[0.06] rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
          />
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {conversations.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs italic">
              No sessions found.
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = activeConvId === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => selectConversation(conv.id)}
                  className={`group p-3 rounded-xl cursor-pointer transition flex items-start gap-3 border ${
                    isActive
                      ? "bg-brand-500/10 border-brand-500/25 text-white"
                      : "bg-[#0c0f17]/40 border-white/[0.03] hover:bg-white/[0.02] text-slate-400"
                  }`}
                >
                  <MessageSquare className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold truncate text-slate-200">{conv.title}</p>
                    <p className="text-[10px] text-slate-500 truncate mt-0.5">
                      {conv.summary || "No description."}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 rounded transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── Main Chat / Workspace Panel ── */}
      <div className="flex-1 flex flex-col bg-slate-900/20 border border-white/[0.05] rounded-2xl overflow-hidden backdrop-blur-xl">
        <div className="px-6 py-4 border-b border-white/[0.05] bg-[#0c0f17]/40 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" /> Active consultation scope
            </h3>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Select one or more indexed corporate files to scope RAG queries.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 max-h-[80px] overflow-y-auto max-w-[400px] border border-white/[0.04] p-2 rounded-xl bg-[#090B12]">
            {documents.length === 0 ? (
              <span className="text-[10px] text-slate-500">No indexed documents available.</span>
            ) : (
              documents.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggleDocSelection(doc.id)}
                    className={`px-2.5 py-1 text-[10px] font-medium rounded-lg transition border flex items-center gap-1.5 ${
                      isSelected
                        ? "bg-brand-500/15 border-brand-500/30 text-brand-400"
                        : "bg-white/[0.02] border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                    }`}
                  >
                    <FileText className="w-3 h-3" />
                    {doc.title}
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-h-[50vh] min-h-[30vh]">
          {messages.length === 0 && !streamingText ? (
            <div className="flex flex-col items-center justify-center text-center h-full py-12">
              <div className="w-12 h-12 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6 text-brand-400" />
              </div>
              <h4 className="text-sm font-bold text-slate-200">Legal Copilot Workspace</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-2">
                Ask multi-turn questions about notices, liabilities, RBI, DPDP, and regulatory audits.
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${
                    msg.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500">
                      {msg.role === "user" ? "You" : "Legal Assistant"}
                    </span>
                  </div>
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed max-w-[80%] whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-brand-505 bg-brand-600 text-white rounded-tr-none"
                        : "bg-[#0c0f17] border border-white/[0.06] text-slate-200 rounded-tl-none shadow-xl"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {msg.role === "assistant" && (
                    <div className="mt-3 space-y-2.5 w-[80%]">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleBookmark(msg)}
                          className="text-[10px] text-brand-400 hover:text-white flex items-center gap-1 bg-brand-500/5 px-2 py-1 rounded-lg border border-brand-500/10 hover:bg-brand-500/20 transition"
                        >
                          <Bookmark className="w-3 h-3" /> Pin to Workspace
                        </button>
                        {msg.needs_review && (
                          <button
                            onClick={() => {
                              setShowReviewId(msg.id || String(index));
                              setEditedText(msg.content);
                            }}
                            className="text-[10px] text-amber-400 hover:text-white flex items-center gap-1 bg-amber-500/5 px-2 py-1 rounded-lg border border-amber-500/10 hover:bg-amber-500/20 transition"
                          >
                            <AlertTriangle className="w-3 h-3" /> Low Confidence (Click to Review)
                          </button>
                        )}
                      </div>

                      {showReviewId === (msg.id || String(index)) && (
                        <div className="bg-[#121826] border border-white/[0.08] p-4 rounded-xl space-y-3 shadow-lg">
                          <h4 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4" /> Human Feedback review
                          </h4>
                          <textarea
                            value={editedText}
                            onChange={(e) => setEditedText(e.target.value)}
                            rows={3}
                            className="w-full text-xs bg-[#090B12] border border-white/[0.06] rounded-lg p-2.5 focus:outline-none focus:border-brand-500 text-slate-200"
                            placeholder="Modify the answer if necessary..."
                          />
                          <input
                            type="text"
                            value={reviewerComment}
                            onChange={(e) => setReviewerComment(e.target.value)}
                            placeholder="Add comment..."
                            className="w-full text-[11px] bg-[#090B12] border border-white/[0.06] rounded-lg p-2 focus:outline-none focus:border-brand-500 text-slate-200"
                          />
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={() => submitReview(index, "APPROVED")}
                              className="px-2.5 py-1 text-[10px] bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-white rounded border border-emerald-500/25 transition"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => submitReview(index, "EDITED")}
                              className="px-2.5 py-1 text-[10px] bg-brand-500/10 hover:bg-brand-500 text-brand-400 hover:text-white rounded border border-brand-500/25 transition"
                            >
                              Edit & Approve
                            </button>
                            <button
                              onClick={() => submitReview(index, "REJECTED")}
                              className="px-2.5 py-1 text-[10px] bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white rounded border border-red-500/25 transition"
                            >
                              Reject
                            </button>
                          </div>
                        </div>
                      )}

                      {msg.citations && msg.citations.length > 0 && (
                        <div className="bg-[#090B12] border border-white/[0.06] rounded-xl p-3.5">
                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                            Source Citations:
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {msg.citations.map((cite, cIdx) => (
                              <Link
                                key={cIdx}
                                href={`/dashboard/documents/${cite.document_id}?page=${cite.page_number}`}
                                className="block p-2 bg-[#0c0f17] hover:bg-brand-500/5 border border-white/[0.05] hover:border-brand-500/20 rounded-lg text-[11px] transition"
                              >
                                <div className="flex justify-between items-center font-semibold text-slate-200">
                                  <span className="truncate">📄 {cite.document_name}</span>
                                  <span className="text-[9px] bg-brand-500/10 text-brand-400 px-1.5 py-0.5 rounded">
                                    Page {cite.page_number}
                                  </span>
                                </div>
                                <div className="text-[9px] text-slate-500 italic mt-1 truncate">
                                  {cite.section} (Match: {Math.round(cite.confidence * 100)}%)
                                </div>
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}

                      {msg.explainability && (
                        <details className="group border border-white/[0.03] bg-[#0c0f17]/20 rounded-xl overflow-hidden text-[10px] text-slate-500">
                          <summary className="px-3 py-2 cursor-pointer font-semibold uppercase tracking-wider text-slate-400 hover:text-white select-none flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <Cpu className="w-3.5 h-3.5 text-brand-400" /> Explainability Diagnostics
                            </span>
                            <ChevronDown className="w-3.5 h-3.5 transform group-open:rotate-180 transition" />
                          </summary>
                          <div className="px-3 pb-3 pt-1.5 space-y-2 border-t border-white/[0.03] font-mono leading-relaxed bg-[#090B12]/40">
                            <div className="flex justify-between">
                              <span>Model Engine:</span>
                              <span className="text-slate-300 font-semibold">{msg.explainability.model_used || "Qwen-2.5 (Local SLM)"}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Total API Latency:</span>
                              <span className="text-slate-300 font-semibold">{msg.explainability.total_latency_ms || 0} ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Retrieval time:</span>
                              <span className="text-slate-300 font-semibold">{msg.explainability.retrieval_latency_ms || 0} ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span>SLM Generation time:</span>
                              <span className="text-slate-300 font-semibold">{msg.explainability.inference_time_ms || 0} ms</span>
                            </div>
                            {msg.explainability.reasoning_summary && (
                              <div className="pt-1.5 border-t border-white/[0.03]">
                                <div className="text-slate-400 font-bold mb-1">Reasoning Summary:</div>
                                <div className="text-slate-300 whitespace-pre-wrap">{msg.explainability.reasoning_summary}</div>
                              </div>
                            )}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {streamingText && (
                <div className="flex flex-col items-start">
                  <span className="text-[10px] uppercase font-bold text-slate-500 mb-1.5">Legal Assistant</span>
                  <div className="p-4 rounded-2xl text-xs leading-relaxed max-w-[80%] whitespace-pre-wrap bg-[#0c0f17] border border-white/[0.06] text-slate-200 rounded-tl-none shadow-xl">
                    {streamingText}
                  </div>
                </div>
              )}
            </>
          )}

          {isGenerating && !streamingText && (
            <div className="flex flex-col items-start animate-pulse">
              <span className="text-[10px] uppercase font-bold text-slate-500 mb-1.5">Legal Assistant</span>
              <div className="flex items-center gap-1.5 bg-[#0c0f17] border border-white/[0.06] p-3 rounded-2xl rounded-tl-none">
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {suggestedQuestions.length > 0 && (
          <div className="px-6 py-2 flex flex-wrap gap-2">
            {suggestedQuestions.map((q, qidx) => (
              <button
                key={qidx}
                onClick={() => handleSend(q)}
                disabled={isGenerating}
                className="px-3 py-1.5 bg-[#0c0f17]/40 hover:bg-brand-500/10 border border-white/[0.05] hover:border-brand-500/25 rounded-full text-[10px] text-slate-300 font-semibold transition"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(query);
          }}
          className="p-6 border-t border-white/[0.05] bg-[#0c0f17]/40 flex gap-3"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isGenerating}
            placeholder="Ask AI Copilot about confidentiality, notice clauses, or compliance guidelines..."
            className="flex-1 bg-[#090B12] border border-white/[0.06] rounded-xl px-4 py-3 text-xs focus:outline-none focus:border-brand-500 text-slate-100 transition placeholder-slate-500"
          />
          <button
            type="submit"
            disabled={isGenerating}
            className="px-5 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/40 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2"
          >
            <Send className="w-3.5 h-3.5" /> Send
          </button>
        </form>
      </div>
    </div>
  );
}
