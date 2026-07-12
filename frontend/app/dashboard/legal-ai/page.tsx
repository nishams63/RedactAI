"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import {
  Shield, Brain, CheckSquare, MessageSquare, BookOpen, AlertTriangle,
  Play, CheckCircle2, XCircle, Send, HelpCircle, UserCheck, RefreshCw, ChevronDown, ChevronUp
} from "lucide-react";

interface ChatMessage {
  sender: "user" | "bot";
  text: string;
  engine?: string;
  confidence?: number;
  timeMs?: number;
  reasoning?: string;
  citations?: any[];
}

export default function LegalAIDashboard() {
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [kbVersion, setKbVersion] = useState<string>("v1.0.0");
  const [chatInput, setChatInput] = useState<string>("Does this document comply with DPDP?");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [expandedCitationIdx, setExpandedCitationIdx] = useState<number | null>(null);
  
  // Human Review Form State
  const [reviewerDecision, setReviewerDecision] = useState<string>("APPROVED");
  const [reviewerComments, setReviewerComments] = useState<string>("");
  const [reviewSubmitted, setReviewSubmitted] = useState<boolean>(false);

  // Fetch documents list
  const { data: docsData, isLoading: docsLoading } = useQuery({
    queryKey: ["documents_list_legal"],
    queryFn: () => apiClient.getDocuments({ page_size: 50, status: "Processed" })
  });
  const documents = docsData?.items || [];

  // Fetch status info (KB version info, registered SLM models)
  const { data: kbData } = useQuery({
    queryKey: ["legal_kb_stats", kbVersion],
    queryFn: () => apiClient.getLegalKnowledge(kbVersion)
  });

  const { data: modelsData } = useQuery({
    queryKey: ["legal_models_stats"],
    queryFn: () => apiClient.getLegalModels()
  });

  // Automatically select the first document if available
  useEffect(() => {
    if (documents.length > 0 && !selectedDocId) {
      setSelectedDocId(documents[0].id);
    }
  }, [documents, selectedDocId]);

  // Mutations for analysis endpoints
  const analyzeMutation = useMutation({
    mutationFn: (id: string) => apiClient.analyzeLegalDocument(id)
  });

  const complianceMutation = useMutation({
    mutationFn: (id: string) => apiClient.checkCompliance(id)
  });

  const summaryMutation = useMutation({
    mutationFn: (id: string) => apiClient.summarizeLegalDocument(id)
  });

  const reviewMutation = useMutation({
    mutationFn: (data: any) => apiClient.submitHumanReview(data)
  });

  // Run initial analysis when document changes
  useEffect(() => {
    if (selectedDocId) {
      analyzeMutation.mutate(selectedDocId);
      complianceMutation.mutate(selectedDocId);
      summaryMutation.mutate(selectedDocId);
      setReviewSubmitted(false);
      setReviewerComments("");
      setChatHistory([
        { sender: "bot", text: "Welcome! Ask me any questions regarding this document's privacy, compliance, or regulatory exposure." }
      ]);
    }
  }, [selectedDocId]);

  // Chat Mutation
  const chatMutation = useMutation({
    mutationFn: (question: string) => apiClient.legalChat(selectedDocId, question, kbVersion),
    onSuccess: (data) => {
      setChatHistory(prev => [
        ...prev,
        {
          sender: "bot",
          text: data.answer,
          engine: data.reasoning_engine,
          confidence: data.confidence,
          timeMs: data.inference_time_ms,
          reasoning: data.reasoning_summary,
          citations: data.citations
        }
      ]);
    },
    onError: (err: any) => {
      setChatHistory(prev => [
        ...prev,
        { sender: "bot", text: `Error generating response: ${err.message || "Engine timeout."}` }
      ]);
    }
  });

  const handleSendChat = () => {
    if (!chatInput.trim() || !selectedDocId) return;
    const q = chatInput;
    setChatHistory(prev => [...prev, { sender: "user", text: q }]);
    setChatInput("");
    chatMutation.mutate(q);
  };

  const handleQuickQuestion = (q: string) => {
    setChatHistory(prev => [...prev, { sender: "user", text: q }]);
    if (!selectedDocId) {
      setTimeout(() => {
        setChatHistory(prev => [
          ...prev,
          { sender: "bot", text: "Please upload and select a legal document from the dropdown first to ask compliance questions." }
        ]);
      }, 300);
      return;
    }
    chatMutation.mutate(q);
  };

  const submitReview = () => {
    if (!selectedDocId || !complianceMutation.data) return;
    
    reviewMutation.mutate({
      document_id: selectedDocId,
      category: "COMPLIANCE",
      ai_recommendation: {
        compliance_score: complianceMutation.data.compliance_score,
        compliance_status: complianceMutation.data.compliance_status,
        violations_count: complianceMutation.data.detected_violations?.length || 0
      },
      reviewer_decision: reviewerDecision,
      reviewer_comments: reviewerComments,
      final_decision: {
        compliance_score: reviewerDecision === "APPROVED" ? complianceMutation.data.compliance_score : 100,
        status: reviewerDecision === "APPROVED" ? complianceMutation.data.compliance_status : "FULLY COMPLIANT"
      }
    }, {
      onSuccess: () => {
        setReviewSubmitted(true);
      }
    });
  };

  const currentDoc = documents.find((d: any) => d.id === selectedDocId);
  const compliance = complianceMutation.data;
  const analysis = analyzeMutation.data;
  const summary = summaryMutation.data;

  // Active models display metrics
  const activeSLM = modelsData?.models?.[0]?.name || "Qwen-2.5-0.5B-Instruct";
  const activeEmbedding = modelsData?.models?.[0]?.embedding_model || "all-MiniLM-L6-v2";
  const activeStore = modelsData?.models?.[0]?.vector_store || "ChromaDB";

  return (
    <div className="space-y-8 animate-fade-in text-[rgb(var(--text-primary))] pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
            <Shield className="w-8 h-8 text-brand-500" />
            Legal AI Privacy Assistant <span className="text-xs bg-brand-500/10 text-brand-400 border border-brand-500/20 px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">Level 3</span>
          </h1>
          <p className="text-[rgb(var(--text-secondary))] mt-1">
            Explainable regulatory compliance, clause-level risk reasoning, and context-backed SLM RAG.
          </p>
        </div>
        
        {/* Document Selector */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-[rgb(var(--text-secondary))] shrink-0">Document Context:</span>
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="px-4 py-2.5 rounded-xl bg-[rgb(var(--bg-card))] border border-[rgb(var(--border-color))]/50 focus:border-brand-500 outline-none text-sm font-semibold max-w-[280px]"
          >
            {docsLoading ? (
              <option>Loading documents...</option>
            ) : documents.length === 0 ? (
              <option>No documents found</option>
            ) : (
              documents.map((d: any) => (
                <option key={d.id} value={d.id}>{d.title}</option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Grid: System Status Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center text-emerald-500">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Knowledge Base</p>
            <p className="text-base font-bold mt-0.5">DPDP & IT Act ({kbVersion})</p>
            <p className="text-xs text-[rgb(var(--text-secondary))] mt-0.5">{kbData?.total_chunks || 12} Indexed Sections</p>
          </div>
        </div>

        <div className="glass-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 bg-violet-500/10 rounded-xl flex items-center justify-center text-violet-500">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Reasoning Model</p>
            <p className="text-base font-bold mt-0.5 truncate max-w-[200px]" title={activeSLM}>{activeSLM}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))] mt-0.5">Local CPU/GPU Inference</p>
          </div>
        </div>

        <div className="glass-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 bg-brand-500/10 rounded-xl flex items-center justify-center text-brand-500">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Embedding Index</p>
            <p className="text-base font-bold mt-0.5">{activeEmbedding}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))] mt-0.5">Cached Store: {activeStore}</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Document Analysis & AI Q&A */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        
        {/* Column Left: Compliance Score, Summaries & Violations */}
        <div className="xl:col-span-7 space-y-6">
          
          {/* Card: Compliance Status Overview */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <CheckSquare className="w-5 h-5 text-brand-500" /> Regulatory Compliance Check
              </h2>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border 
                ${compliance?.compliance_status === "FULLY COMPLIANT" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : 
                  compliance?.compliance_status === "PARTIALLY COMPLIANT" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : 
                  "bg-red-500/10 text-red-400 border-red-500/20"}`}
              >
                {complianceMutation.isPending ? "Analyzing..." : compliance?.compliance_status || "Unknown"}
              </span>
            </div>

            <div className="flex flex-col md:flex-row items-center gap-8">
              {/* Compliance Score Dial */}
              <div className="relative w-36 h-36 flex items-center justify-center shrink-0">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" stroke="rgb(var(--border-color))" strokeWidth="6" fill="transparent" opacity="0.3" />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke={compliance?.compliance_score >= 80 ? "rgb(16, 185, 129)" : compliance?.compliance_score >= 60 ? "rgb(245, 158, 11)" : "rgb(239, 68, 68)"}
                    strokeWidth="6"
                    fill="transparent"
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 - (251.2 * (compliance?.compliance_score || 0)) / 100}
                    className="transition-all duration-1000 ease-out"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold">{complianceMutation.isPending ? "..." : compliance?.compliance_score}</span>
                  <span className="text-[10px] text-[rgb(var(--text-secondary))] font-bold uppercase tracking-wider">Score</span>
                </div>
              </div>

              {/* Violations and Risks checklist */}
              <div className="flex-1 space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-[rgb(var(--text-secondary))]">Violations Checklist</h3>
                {complianceMutation.isPending ? (
                  <div className="space-y-2">
                    <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
                    <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse w-3/4" />
                  </div>
                ) : !compliance?.detected_violations || compliance.detected_violations.length === 0 ? (
                  <div className="flex items-center gap-2.5 text-emerald-400 text-sm font-semibold">
                    <CheckCircle2 className="w-5 h-5 shrink-0" />
                    Passed all structural policy guidelines (DPDP Act, Corporate Rules).
                  </div>
                ) : (
                  <div className="space-y-3">
                    {compliance.detected_violations.map((v: any, idx: number) => (
                      <div key={idx} className="p-3.5 bg-red-500/5 rounded-xl border border-red-500/10 flex gap-3">
                        <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wide text-red-400">{v.rule}</p>
                          <p className="text-sm font-medium mt-1 text-[rgb(var(--text-primary))]">{v.issue}</p>
                          <p className="text-xs text-[rgb(var(--text-secondary))] mt-1.5"><span className="font-bold text-brand-400">Required Action:</span> {v.remedy}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Card: Document Summaries */}
          <div className="glass-card p-6 space-y-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-brand-500" /> Privacy & Legal Summary
            </h2>
            
            {summaryMutation.isPending ? (
              <div className="space-y-4 py-4">
                <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
                <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse w-5/6" />
                <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse w-2/3" />
              </div>
            ) : (
              <div className="space-y-4 divide-y divide-[rgb(var(--border-color))]/30">
                <div className="pt-1">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-brand-400">Executive Summary</h3>
                  <p className="text-sm font-medium text-[rgb(var(--text-primary))] mt-1">{summary?.executive_summary}</p>
                </div>
                <div className="pt-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-violet-400">Compliance & Privacy Risks</h3>
                  <p className="text-sm text-[rgb(var(--text-secondary))] mt-1">{summary?.compliance_summary}</p>
                  <p className="text-sm text-[rgb(var(--text-secondary))] mt-1.5">{summary?.risk_summary}</p>
                </div>
                <div className="pt-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400">Privacy Action Items</h3>
                  <ul className="list-disc pl-5 text-sm text-[rgb(var(--text-secondary))] mt-1.5 space-y-1">
                    {summary?.action_items?.map((item: string, idx: number) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Card: Clause-Level Privacy Reasoning Table */}
          <div className="glass-card p-6">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
              <Brain className="w-5 h-5 text-brand-500" /> Clause-Level Risk Analysis
            </h2>

            {analyzeMutation.isPending ? (
              <div className="space-y-2 py-4">
                <div className="h-6 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
                <div className="h-6 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
              </div>
            ) : !analysis?.clauses || analysis.clauses.length === 0 ? (
              <p className="text-center py-8 text-sm text-[rgb(var(--text-secondary))]">No clauses extracted.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[rgb(var(--border-color))]/50 text-[rgb(var(--text-secondary))] font-bold">
                      <th className="py-3 px-4">Clause Preview</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Sensitive Data</th>
                      <th className="py-3 px-4 text-center">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.clauses.map((c: any, idx: number) => (
                      <tr key={idx} className="border-b border-[rgb(var(--border-color))]/30 hover:bg-[rgb(var(--bg-secondary))]/30 transition-colors">
                        <td className="py-3 px-4 max-w-[280px] font-medium truncate" title={c.clause_text}>{c.clause_text}</td>
                        <td className="py-3 px-4 text-xs font-bold text-brand-400">{c.clause_type}</td>
                        <td className="py-3 px-4 text-xs">
                          {c.sensitive_data.length === 0 ? (
                            <span className="text-[rgb(var(--text-secondary))]">None</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {c.sensitive_data.map((s: string, i: number) => (
                                <span key={i} className="px-2 py-0.5 bg-red-500/10 text-red-400 rounded-full border border-red-500/20">{s}</span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase border
                            ${c.risk_level === "HIGH" ? "bg-red-500/10 text-red-400 border-red-500/20" : 
                              c.risk_level === "MEDIUM" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : 
                              "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"}`}
                          >
                            {c.risk_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Column Right: Interactive Explainable AI Chat & Human Review Workflow */}
        <div className="xl:col-span-5 space-y-6">
          
          {/* Card: RAG Q&A Chat Window */}
          <div className="glass-card p-5 flex flex-col h-[520px]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-4 shrink-0">
              <MessageSquare className="w-5 h-5 text-brand-500" /> Explainable Privacy Chat
            </h2>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4 select-none scrollbar-thin">
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                  <div className={`p-3.5 rounded-2xl max-w-[85%] text-sm font-medium leading-relaxed
                    ${msg.sender === "user" ? "bg-brand-500 text-white rounded-tr-none" : "bg-[rgb(var(--bg-secondary))] text-[rgb(var(--text-primary))] rounded-tl-none border border-[rgb(var(--border-color))]/50"}`}
                  >
                    {msg.text}
                  </div>

                  {/* Explainability metadata block for bot response */}
                  {msg.sender === "bot" && msg.engine && (
                    <div className="mt-2 w-[90%] p-3 bg-[rgb(var(--bg-secondary))]/50 border border-[rgb(var(--border-color))]/30 rounded-xl space-y-2">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] font-bold text-[rgb(var(--text-secondary))]">
                        <span>Engine: <span className="text-brand-400">{msg.engine}</span></span>
                        <span>Confidence: <span className="text-emerald-400">{msg.confidence !== undefined ? Math.round(msg.confidence * 100) : 0}%</span></span>
                        <span>Latency: <span className="text-violet-400">{msg.timeMs !== undefined ? msg.timeMs : 0}ms</span></span>
                      </div>
                      
                      <p className="text-[11px] text-[rgb(var(--text-secondary))] leading-relaxed font-medium">
                        <span className="font-bold text-[rgb(var(--text-primary))]">Reasoning:</span> {msg.reasoning}
                      </p>

                      {/* Collapsible Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="border-t border-[rgb(var(--border-color))]/30 pt-1.5 mt-1.5">
                          <button
                            onClick={() => setExpandedCitationIdx(expandedCitationIdx === idx ? null : idx)}
                            className="flex items-center gap-1.5 text-[10px] font-extrabold text-brand-400 hover:text-brand-500 uppercase tracking-wider"
                          >
                            Citations ({msg.citations.length})
                            {expandedCitationIdx === idx ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                          
                          {expandedCitationIdx === idx && (
                            <div className="mt-2 space-y-2 animate-slide-down">
                              {msg.citations.map((c: any, cidx: number) => (
                                <div key={cidx} className={`p-2 rounded-lg text-[10px] leading-relaxed font-medium border 
                                  ${c.is_hallucinated ? "bg-red-500/5 border-red-500/10 text-red-300" : "bg-emerald-500/5 border-emerald-500/10 text-emerald-300"}`}
                                >
                                  <span className="font-extrabold block text-[11px]">
                                    {c.citation} {c.is_hallucinated ? "(Hallucination Warning)" : "(Verified Source)"}
                                  </span>
                                  Referenced: {c.referenced_source} (Section: {c.section_number})
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {chatMutation.isPending && (
                <div className="flex items-center gap-2.5 text-xs text-[rgb(var(--text-secondary))] mt-2 font-bold italic">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Local SLM reasoning in progress...
                </div>
              )}
            </div>

            {/* Quick Questions prompts */}
            <div className="flex flex-wrap gap-1.5 mb-3 shrink-0">
              <button
                onClick={() => handleQuickQuestion("Why is this document Confidential?")}
                className="px-2.5 py-1.5 bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))]/50 hover:bg-brand-500/10 rounded-xl text-[10px] font-bold transition-all text-brand-400 hover:border-brand-500/30"
              >
                Why Confidential?
              </button>
              <button
                onClick={() => handleQuickQuestion("Does this document comply with DPDP?")}
                className="px-2.5 py-1.5 bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))]/50 hover:bg-brand-500/10 rounded-xl text-[10px] font-bold transition-all text-brand-400 hover:border-brand-500/30"
              >
                Does it comply with DPDP?
              </button>
              <button
                onClick={() => handleQuickQuestion("Summarize all privacy risks.")}
                className="px-2.5 py-1.5 bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))]/50 hover:bg-brand-500/10 rounded-xl text-[10px] font-bold transition-all text-brand-400 hover:border-brand-500/30"
              >
                Summarize risks
              </button>
            </div>

            {/* Input Bar */}
            <div className="flex gap-2.5 shrink-0">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                placeholder="Ask a compliance or privacy question..."
                className="flex-1 px-4 py-3 rounded-xl bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))]/50 focus:border-brand-500 outline-none text-sm font-medium"
              />
              <button
                onClick={handleSendChat}
                className="w-12 h-12 bg-brand-500 hover:bg-brand-600 active:scale-95 transition-all text-white rounded-xl flex items-center justify-center shrink-0"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Card: Human-in-the-Loop Review Workflow */}
          <div className="glass-card p-6 space-y-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-brand-500" /> Human Review Feedback
            </h2>
            <p className="text-xs text-[rgb(var(--text-secondary))] leading-relaxed font-semibold">
              Approve compliance rating or override AI findings. Captured review logs directly support future Small Language Model reinforcement.
            </p>

            {reviewSubmitted ? (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl flex items-center gap-2.5 text-sm font-semibold">
                <CheckCircle2 className="w-5 h-5 shrink-0" />
                Review submitted successfully! Decisions logged to model training loop.
              </div>
            ) : (
              <div className="space-y-4.5">
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-sm font-bold cursor-pointer select-none">
                    <input
                      type="radio"
                      name="decision"
                      value="APPROVED"
                      checked={reviewerDecision === "APPROVED"}
                      onChange={() => setReviewerDecision("APPROVED")}
                      className="accent-brand-500"
                    />
                    Approve AI Recommendations
                  </label>
                  <label className="flex items-center gap-2 text-sm font-bold cursor-pointer select-none">
                    <input
                      type="radio"
                      name="decision"
                      value="OVERRIDDEN"
                      checked={reviewerDecision === "OVERRIDDEN"}
                      onChange={() => setReviewerDecision("OVERRIDDEN")}
                      className="accent-brand-500"
                    />
                    Override / Force Compliant
                  </label>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-[rgb(var(--text-secondary))] block">Reviewer Notes & Feedback</label>
                  <textarea
                    value={reviewerComments}
                    onChange={(e) => setReviewerComments(e.target.value)}
                    placeholder="Provide details about compliance gaps or reasoning overrides..."
                    rows={3}
                    className="w-full px-4 py-3 rounded-xl bg-[rgb(var(--bg-secondary))] border border-[rgb(var(--border-color))]/50 focus:border-brand-500 outline-none text-sm font-medium resize-none"
                  />
                </div>

                <button
                  onClick={submitReview}
                  disabled={reviewMutation.isPending || !compliance}
                  className="w-full py-3 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-700 active:scale-95 transition-all text-white font-bold rounded-xl text-sm flex items-center justify-center gap-2"
                >
                  {reviewMutation.isPending ? "Logging review..." : "Log Decisions & Feedback"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
