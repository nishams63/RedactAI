"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import {
  TrendingUp, CheckSquare, Settings, Play, Database, History,
  PlusCircle, RefreshCw, AlertTriangle, ShieldCheck, Clock, CheckCircle2, ChevronRight
} from "lucide-react";

export default function AIQualityPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "prompts" | "history">("overview");
  const [showAddPromptModal, setShowAddPromptModal] = useState(false);
  const [useSLMForBenchmark, setUseSLMForBenchmark] = useState(false);

  // New Prompt Form State
  const [promptId, setPromptId] = useState("rag_qa_template");
  const [version, setVersion] = useState("v1.1.0");
  const [template, setTemplate] = useState(
    "You are a helpful assistant. Use these docs: {context}\nQuestion: {question}"
  );
  const [assocModel, setAssocModel] = useState("Qwen-2.5-0.5B-Instruct");
  const [kbVersion, setKbVersion] = useState("v1.0.0");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Queries
  const { data: qualityData, isLoading: qualityLoading, refetch: refetchQuality } = useQuery({
    queryKey: ["ai_quality_metrics"],
    queryFn: () => apiClient.getAIQualityMetrics()
  });

  const { data: promptsData, isLoading: promptsLoading, refetch: refetchPrompts } = useQuery({
    queryKey: ["ai_prompts", promptId],
    queryFn: () => apiClient.getVersionedPrompts(promptId)
  });

  // Mutations
  const benchmarkMutation = useMutation({
    mutationFn: (useSlm: boolean) => apiClient.runAIQualityBenchmark(useSlm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai_quality_metrics"] });
      queryClient.invalidateQueries({ queryKey: ["ai_prompts"] });
    }
  });

  const registerPromptMutation = useMutation({
    mutationFn: (payload: {
      prompt_id: string;
      version: string;
      template: string;
      associated_model: string;
      kb_version: string;
    }) => apiClient.registerPrompt(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai_prompts"] });
      setShowAddPromptModal(false);
      setSuccessMsg("Prompt template version registered successfully!");
      setTimeout(() => setSuccessMsg(""), 4000);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || "Failed to register prompt version.");
      setTimeout(() => setErrorMsg(""), 4000);
    }
  });

  const handleRunBenchmark = () => {
    benchmarkMutation.mutate(useSLMForBenchmark);
  };

  const handleRegisterPromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptId || !version || !template || !assocModel || !kbVersion) {
      setErrorMsg("All fields are required.");
      return;
    }
    registerPromptMutation.mutate({
      prompt_id: promptId,
      version,
      template,
      associated_model: assocModel,
      kb_version: kbVersion
    });
  };

  const latest = qualityData?.latest || {};
  const history = qualityData?.history || [];
  const activePrompt = promptsData?.active || {};
  const promptHistory = promptsData?.history || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Quality & Retrieval Stabilization</h1>
          <p className="text-[rgb(var(--text-secondary))] mt-1">
            Monitor retrieval MRR, validation rates, calibrated confidence calibration, and manage RAG prompt version history.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-[rgb(var(--text-secondary))]">
            <input
              type="checkbox"
              checked={useSLMForBenchmark}
              onChange={(e) => setUseSLMForBenchmark(e.target.checked)}
              className="rounded bg-[rgb(var(--bg-card))] border-[rgb(var(--border-color))]"
            />
            Use Local SLM Model (longer run time)
          </label>
          <button
            onClick={handleRunBenchmark}
            disabled={benchmarkMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {benchmarkMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Suite...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Run Quality Benchmark</span>
              </>
            )}
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl flex items-center gap-2">
          <ShieldCheck className="w-5 h-5" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Tabs Menu */}
      <div className="border-b border-[rgb(var(--border-color))]/50 flex gap-6">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-4 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "overview"
              ? "border-brand-500 text-[rgb(var(--text-primary))]"
              : "border-transparent text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Overview Metrics
        </button>
        <button
          onClick={() => setActiveTab("prompts")}
          className={`pb-4 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "prompts"
              ? "border-brand-500 text-[rgb(var(--text-primary))]"
              : "border-transparent text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
          }`}
        >
          <Settings className="w-4 h-4" />
          Prompt Version Registry
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`pb-4 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "history"
              ? "border-brand-500 text-[rgb(var(--text-primary))]"
              : "border-transparent text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
          }`}
        >
          <History className="w-4 h-4" />
          Benchmark Execution Logs ({history.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "overview" && (
        <div className="space-y-8 animate-fadeIn">
          {/* Highlight metrics cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="card p-6 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Mean Reciprocal Rank (MRR)</p>
                <h3 className="text-4xl font-bold mt-2 gradient-text">{latest?.retrieval_metrics?.mrr || "0.00"}</h3>
              </div>
              <div className="mt-4 pt-4 border-t border-[rgb(var(--border-color))]/30">
                <span className="text-xs text-[rgb(var(--text-secondary))]">Retrieval Rank Precision</span>
              </div>
            </div>

            <div className="card p-6 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Recall @ 5</p>
                <h3 className="text-4xl font-bold mt-2 text-indigo-400">{(latest?.retrieval_metrics?.recall_5 * 100)?.toFixed(0) || "0"}%</h3>
              </div>
              <div className="mt-4 pt-4 border-t border-[rgb(var(--border-color))]/30">
                <span className="text-xs text-[rgb(var(--text-secondary))]">Ground Truth inside Top 5</span>
              </div>
            </div>

            <div className="card p-6 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Citation Correctness</p>
                <h3 className="text-4xl font-bold mt-2 text-emerald-400">{(latest?.citation_metrics?.citation_correctness * 100)?.toFixed(0) || "0"}%</h3>
              </div>
              <div className="mt-4 pt-4 border-t border-[rgb(var(--border-color))]/30">
                <span className="text-xs text-[rgb(var(--text-secondary))]">Verified vs Hallucinated claims</span>
              </div>
            </div>

            <div className="card p-6 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-[rgb(var(--text-secondary))] uppercase tracking-wider">Avg Calibrated Confidence</p>
                <h3 className="text-4xl font-bold mt-2 text-amber-400">{(latest?.confidence_calibration?.average_confidence * 100)?.toFixed(0) || "0"}%</h3>
              </div>
              <div className="mt-4 pt-4 border-t border-[rgb(var(--border-color))]/30">
                <span className="text-xs text-[rgb(var(--text-secondary))]">Integrated reliability estimate</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Confidence distribution chart using SVG */}
            <div className="card p-6 flex flex-col justify-between lg:col-span-1">
              <div>
                <h4 className="text-lg font-bold">Confidence Distribution Bins</h4>
                <p className="text-xs text-[rgb(var(--text-secondary))] mt-1">Calibration count distribution for past run.</p>
              </div>
              <div className="mt-6 flex flex-col gap-4">
                {Object.entries(latest?.confidence_calibration?.confidence_bins || {}).map(([bin, val]: any) => {
                  const total = Object.values(latest?.confidence_calibration?.confidence_bins || {}).reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = total > 0 ? (val / total) * 100 : 0;
                  return (
                    <div key={bin} className="space-y-2">
                      <div className="flex justify-between text-xs font-medium">
                        <span>{bin} Confidence</span>
                        <span className="text-[rgb(var(--text-secondary))]">{val} questions ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="h-2.5 w-full bg-[rgb(var(--bg-primary))] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-brand-500 to-indigo-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Citation Quality parameters */}
            <div className="card p-6 flex flex-col lg:col-span-2 space-y-6">
              <div>
                <h4 className="text-lg font-bold">Citation & Evidence Verification Rate</h4>
                <p className="text-xs text-[rgb(var(--text-secondary))] mt-1">Measuring RAG alignment and safety constraints.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
                <div className="p-4 bg-[rgb(var(--bg-primary))]/50 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="text-sm font-semibold">Citation Coverage</span>
                  </div>
                  <p className="text-2xl font-bold">{(latest?.citation_metrics?.citation_coverage * 100)?.toFixed(0)}%</p>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">% of referenced contexts cited in output answer.</p>
                </div>

                <div className="p-4 bg-[rgb(var(--bg-primary))]/50 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-rose-400">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="text-sm font-semibold">Unsupported Claims</span>
                  </div>
                  <p className="text-2xl font-bold">{latest?.citation_metrics?.unsupported_claims_count || 0}</p>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Total references not backed by retrieved contexts.</p>
                </div>

                <div className="p-4 bg-[rgb(var(--bg-primary))]/50 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-indigo-400">
                    <Clock className="w-5 h-5" />
                    <span className="text-sm font-semibold">Average Latency</span>
                  </div>
                  <p className="text-2xl font-bold">{latest?.latency_ms || latest?.latency || 0} ms</p>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Benchmark QA processing latency.</p>
                </div>
              </div>

              {latest?.regression_status && (
                <div className={`p-4 rounded-xl flex items-center justify-between border ${
                  latest.regression_status === "IMPROVED"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : latest.regression_status === "REGRESSED"
                    ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                    : "bg-[rgb(var(--bg-primary))]/50 border-[rgb(var(--border-color))]/50 text-[rgb(var(--text-secondary))]"
                }`}>
                  <div className="flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    <div>
                      <p className="text-sm font-semibold">Regression Status vs Previous Run</p>
                      <p className="text-xs opacity-80">Comparing current MRR score against previous test cycle.</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold uppercase tracking-wider px-3 py-1 bg-black/10 rounded-lg">{latest.regression_status}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "prompts" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fadeIn">
          {/* Active prompt details */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6 space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-lg font-bold">Active Prompt Template Details</h3>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Stored in persistent Prompt Registry.</p>
                </div>
                <button
                  onClick={() => setShowAddPromptModal(true)}
                  className="btn-secondary flex items-center gap-2 text-xs"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Register Version</span>
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm p-4 bg-[rgb(var(--bg-primary))]/50 rounded-xl">
                <div>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Prompt ID</p>
                  <p className="font-semibold truncate">{activePrompt?.prompt_id || "rag_qa_template"}</p>
                </div>
                <div>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Active Version</p>
                  <p className="font-semibold">{activePrompt?.version || "v1.0.0"}</p>
                </div>
                <div>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Associated Model</p>
                  <p className="font-semibold truncate">{activePrompt?.associated_model || "Qwen-2.5-0.5B-Instruct"}</p>
                </div>
                <div>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">KB Version</p>
                  <p className="font-semibold">{activePrompt?.kb_version || "v1.0.0"}</p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold">Active Template string:</p>
                <pre className="p-4 bg-[rgb(var(--bg-primary))] rounded-xl text-xs overflow-x-auto border border-[rgb(var(--border-color))]/50 font-mono text-[rgb(var(--text-primary))]">
                  {activePrompt?.template}
                </pre>
              </div>
            </div>
          </div>

          {/* Prompts history */}
          <div className="lg:col-span-1 space-y-6">
            <div className="card p-6 space-y-4">
              <div>
                <h3 className="text-lg font-bold">Prompt Version History</h3>
                <p className="text-xs text-[rgb(var(--text-secondary))]">List of all saved prompt templates in the registry.</p>
              </div>

              <div className="space-y-4 divide-y divide-[rgb(var(--border-color))]/30">
                {promptHistory.map((p: any, idx: number) => (
                  <div key={p.version} className={`pt-4 ${idx === 0 ? "pt-0 border-t-0" : ""}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-bold px-2 py-0.5 bg-brand-500/10 text-brand-400 rounded-md">
                          {p.version}
                        </span>
                        <p className="text-xs text-[rgb(var(--text-secondary))] mt-1">Model: {p.associated_model}</p>
                      </div>
                      <p className="text-xs text-[rgb(var(--text-secondary))]">
                        {new Date(p.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mt-3 text-xs bg-[rgb(var(--bg-primary))]/50 p-2 rounded-lg">
                      <div>
                        <p className="text-[rgb(var(--text-secondary))]">Benchmark MRR</p>
                        <p className="font-semibold">{p.metrics?.mrr || "0.85"}</p>
                      </div>
                      <div>
                        <p className="text-[rgb(var(--text-secondary))]">Benchmark Recall</p>
                        <p className="font-semibold">{p.metrics?.recall_5 || "1.0"}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="card p-6 space-y-6 animate-fadeIn">
          <div>
            <h3 className="text-lg font-bold">Historical Benchmark Runs</h3>
            <p className="text-xs text-[rgb(var(--text-secondary))]">Immutable execution results stored in the database.</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-[rgb(var(--text-primary))]">
              <thead className="bg-[rgb(var(--bg-primary))] text-xs uppercase text-[rgb(var(--text-secondary))]">
                <tr>
                  <th className="px-6 py-4 rounded-l-xl">Date & Time</th>
                  <th className="px-6 py-4">Prompt Version</th>
                  <th className="px-6 py-4">Model</th>
                  <th className="px-6 py-4">Recall@5</th>
                  <th className="px-6 py-4">MRR</th>
                  <th className="px-6 py-4">Citation Correctness</th>
                  <th className="px-6 py-4">Latency (avg)</th>
                  <th className="px-6 py-4 rounded-r-xl">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgb(var(--border-color))]/30">
                {history.map((run: any) => (
                  <tr key={run.id} className="hover:bg-[rgb(var(--bg-primary))]/30">
                    <td className="px-6 py-4 font-medium text-xs">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs font-semibold">{run.prompt_version}</td>
                    <td className="px-6 py-4 text-xs text-[rgb(var(--text-secondary))] truncate max-w-[150px]">{run.model_version}</td>
                    <td className="px-6 py-4 text-xs">{(run.retrieval_metrics?.recall_5 * 100).toFixed(0)}%</td>
                    <td className="px-6 py-4 text-xs font-bold">{run.retrieval_metrics?.mrr}</td>
                    <td className="px-6 py-4 text-xs">{(run.citation_metrics?.citation_correctness * 100).toFixed(0)}%</td>
                    <td className="px-6 py-4 text-xs">{run.latency} ms</td>
                    <td className="px-6 py-4 text-xs">
                      <span className={`px-2.5 py-1 rounded-full text-xxs font-bold uppercase tracking-wider ${
                        run.regression_status === "IMPROVED"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : run.regression_status === "REGRESSED"
                          ? "bg-rose-500/10 text-rose-400"
                          : "bg-gray-500/10 text-gray-400"
                      }`}>
                        {run.regression_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Register Prompt Modal */}
      {showAddPromptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="card w-full max-w-xl p-6 space-y-6 max-h-[90vh] overflow-y-auto animate-fadeIn">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold">Register New Prompt Version</h3>
              <button
                onClick={() => setShowAddPromptModal(false)}
                className="text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))]"
              >
                Cancel
              </button>
            </div>

            <form onSubmit={handleRegisterPromptSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[rgb(var(--text-secondary))]">Prompt ID</label>
                <input
                  type="text"
                  value={promptId}
                  onChange={(e) => setPromptId(e.target.value)}
                  className="input w-full"
                  disabled
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-[rgb(var(--text-secondary))]">Version Tag (e.g. v1.1.0)</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  className="input w-full font-semibold"
                  placeholder="v1.1.0"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-[rgb(var(--text-secondary))]">Associated Model</label>
                <input
                  type="text"
                  value={assocModel}
                  onChange={(e) => setAssocModel(e.target.value)}
                  className="input w-full"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-[rgb(var(--text-secondary))]">Knowledge Base Version</label>
                <input
                  type="text"
                  value={kbVersion}
                  onChange={(e) => setKbVersion(e.target.value)}
                  className="input w-full"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-[rgb(var(--text-secondary))]">Prompt Template</label>
                <textarea
                  rows={6}
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="input w-full font-mono text-xs"
                />
              </div>

              <button
                type="submit"
                disabled={registerPromptMutation.isPending}
                className="btn-primary w-full py-3"
              >
                {registerPromptMutation.isPending ? "Registering..." : "Submit New Version"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
