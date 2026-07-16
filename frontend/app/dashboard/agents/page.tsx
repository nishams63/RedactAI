"use client";

import React, { useState, useEffect } from "react";
import { agentsService } from "@/services/agents";
import { apiClient } from "@/services/api";
import {
  Activity, Play, CheckCircle2, AlertCircle, Clock, Server, ToggleLeft, ToggleRight, ListTodo, ShieldCheck, Terminal, Compass, RefreshCw
} from "lucide-react";

export default function AgentMonitorDashboardPage() {
  const [registry, setRegistry] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  
  const [prompt, setPrompt] = useState<string>("Is this document compliant with DPDP rules?");
  const [loading, setLoading] = useState<boolean>(false);
  const [outcome, setOutcome] = useState<any>(null);

  const loadDashboardData = async () => {
    try {
      const reg = await agentsService.getRegistry();
      setRegistry(reg || []);
      const met = await agentsService.getHealthMetrics();
      setMetrics(met || []);
    } catch (err) {
      console.error("Failed to load metrics or registry data", err);
    }
  };

  const loadDocs = async () => {
    try {
      const res = await apiClient.getDocuments();
      setDocuments(res.documents || []);
      if (res.documents && res.documents.length > 0) {
        setSelectedDocIds([res.documents[0].id]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadDashboardData();
    loadDocs();
  }, []);

  const handleToggleActive = async (agentId: string, version: string, currentStatus: boolean) => {
    try {
      await agentsService.toggleAgentActivation(agentId, version, !currentStatus);
      loadDashboardData();
    } catch (err) {
      console.error("Toggle agent failed", err);
    }
  };

  const handleExecute = async () => {
    if (!prompt) return;
    setLoading(true);
    setOutcome(null);
    try {
      const res = await agentsService.executeWorkflow(prompt, selectedDocIds);
      setOutcome(res);
      loadDashboardData();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-slate-100 font-sans space-y-6 flex flex-col h-[85vh] overflow-y-auto pr-1">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.06] pb-4 shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-brand-500 animate-pulse" /> Enterprise Agent Platform Monitor
          </h1>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Monitor single-responsibility sub-agents, dynamic intent planners, execution logs, and health metrics.
          </p>
        </div>
        <button
          onClick={loadDashboardData}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 border border-white/[0.08] hover:bg-slate-800 text-xs text-slate-300 rounded-xl transition"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Metrics
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        <div className="lg:col-span-2 space-y-6 flex flex-col min-h-0">
          <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-5 space-y-4">
            <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-4 h-4 text-brand-500" /> Dynamic Task Planner & Execution Panel
            </h2>
            <div className="space-y-4 text-xs">
              <div className="flex flex-col gap-2">
                <span className="text-slate-500">Query prompt:</span>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="bg-slate-950/60 border border-white/[0.08] rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-brand-500 min-h-[70px] resize-none"
                  placeholder="Ask a legal query requiring agent task planning..."
                />
              </div>

              <div className="flex items-center gap-4">
                <div className="flex-1 flex flex-col gap-1">
                  <span className="text-slate-500 text-[10px]">Reference Document:</span>
                  <select
                    multiple
                    value={selectedDocIds}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                      setSelectedDocIds(selected);
                    }}
                    className="bg-slate-950/60 border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    {documents.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.title}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleExecute}
                  disabled={loading}
                  className="h-10 px-6 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/30 text-white font-bold rounded-xl flex items-center justify-center gap-1.5 transition text-xs shrink-0 self-end"
                >
                  <Play className="w-4 h-4" /> {loading ? "Invoking agents..." : "Execute Workflow"}
                </button>
              </div>
            </div>
          </div>

          {outcome && (
            <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-5 space-y-4 flex-1 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-white/[0.04] pb-3">
                <h3 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Completed Task Details
                </h3>
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-bold">
                  Confidence: {Math.round(outcome.confidence_score * 100)}%
                </span>
              </div>

              {outcome.explainability && (
                <div className="grid grid-cols-2 gap-4 text-xs pt-1">
                  <div className="bg-[#090B12]/40 border border-white/[0.03] p-3 rounded-xl">
                    <span className="text-slate-500 text-[10px] uppercase block">Detected Intent</span>
                    <p className="text-slate-200 font-bold mt-0.5 uppercase">{outcome.explainability.reasoning_summary ? "Matched Intent" : "General"}</p>
                  </div>
                  <div className="bg-[#090B12]/40 border border-white/[0.03] p-3 rounded-xl">
                    <span className="text-slate-500 text-[10px] uppercase block">Involved Agents</span>
                    <p className="text-brand-400 font-bold mt-0.5">
                      {outcome.explainability.agents_involved?.join(", ") || "Retrieval Agent"}
                    </p>
                  </div>
                </div>
              )}

              {outcome.explainability?.execution_steps_log && (
                <div className="space-y-2">
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Execution Timeline Gantt:</span>
                  <div className="space-y-1.5 max-h-[140px] overflow-y-auto bg-slate-950/40 p-3 rounded-xl border border-white/[0.03]">
                    {outcome.explainability.execution_steps_log.map((log: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-2.5 text-[11px] py-1 border-b border-white/[0.02] last:border-0">
                        <Clock className="w-3.5 h-3.5 text-brand-400 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <span className="font-bold text-slate-300 mr-2">[{log.agent}]</span>
                          <span className="text-slate-400">{log.msg}</span>
                        </div>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          log.status === "success" ? "bg-emerald-500/10 text-emerald-400" : "bg-brand-500/10 text-brand-400"
                        }`}>
                          {log.status.toUpperCase()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2 border-t border-white/[0.04]">
                <span className="text-slate-500 text-[10px] uppercase font-bold block">Aggregated Answer Output:</span>
                <div className="bg-slate-950/80 border border-white/[0.05] rounded-xl p-4 text-xs leading-normal max-h-[200px] overflow-y-auto text-slate-200">
                  {outcome.answer}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6 overflow-y-auto pr-1">
          <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-5 space-y-4">
            <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
              <Server className="w-4 h-4 text-brand-500" /> Active Agent Registry
            </h2>
            <div className="space-y-3.5">
              {registry.map((agent) => (
                <div key={agent.id} className="bg-[#090B12]/60 border border-white/[0.03] p-3.5 rounded-xl space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-bold text-slate-200 text-xs block">{agent.name}</span>
                      <span className="text-[9px] text-slate-500 font-mono">ID: {agent.agent_id} (v{agent.version})</span>
                    </div>
                    <button
                      onClick={() => handleToggleActive(agent.agent_id, agent.version, agent.is_active)}
                      className="text-slate-400 hover:text-slate-200 transition"
                    >
                      {agent.is_active ? (
                        <ToggleRight className="w-6 h-6 text-brand-500" />
                      ) : (
                        <ToggleLeft className="w-6 h-6 text-slate-600" />
                      )}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.map((cap: string) => (
                      <span key={cap} className="text-[8px] bg-brand-500/10 text-brand-400 px-1.5 py-0.5 rounded font-bold font-mono">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-5 space-y-4">
            <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
              <Server className="w-4 h-4 text-brand-500" /> Observability metrics
            </h2>
            <div className="space-y-3.5 text-[11px]">
              {metrics.map((metric) => (
                <div key={metric.agent_id} className="bg-[#090B12]/60 border border-white/[0.03] p-3 rounded-xl space-y-2">
                  <span className="font-bold text-slate-200 block">{metric.agent_id}</span>
                  <div className="grid grid-cols-2 gap-2 text-center text-[10px]">
                    <div className="bg-slate-900/40 p-1.5 rounded">
                      <span className="text-slate-500 uppercase text-[8px] block">Success Count</span>
                      <span className="text-emerald-400 font-bold">{metric.success_count}</span>
                    </div>
                    <div className="bg-slate-900/40 p-1.5 rounded">
                      <span className="text-slate-500 uppercase text-[8px] block">Failure Count</span>
                      <span className="text-brand-400 font-bold">{metric.failure_count}</span>
                    </div>
                    <div className="bg-slate-900/40 p-1.5 rounded">
                      <span className="text-slate-500 uppercase text-[8px] block">Avg Latency</span>
                      <span className="text-slate-300 font-bold">{metric.avg_latency_ms} ms</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
