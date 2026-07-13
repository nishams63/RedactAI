"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import {
  FileText, CheckCircle2, Clock, Users,
  TrendingUp, Activity, ArrowUpRight, Shield, Globe, Terminal, ShieldAlert
} from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiClient.getDashboard(),
  });

  const stats = data?.stats;
  const activity = data?.recent_activity || [];
  const recentJobs = data?.recent_jobs || [];

  const statIcons = [
    { key: "total_documents", label: "Total Documents", value: stats?.total_documents ?? 0, icon: FileText, color: "#4F7CFF", gradient: "linear-gradient(135deg, rgba(79,124,255,0.12), rgba(79,124,255,0.04))" },
    { key: "total_pages", label: "Pages Processed", value: stats?.total_pages ?? 0, icon: Globe, color: "#00E1C7", gradient: "linear-gradient(135deg, rgba(0,225,199,0.12), rgba(0,225,199,0.04))" },
    { key: "total_entities", label: "Entities Flagged", value: stats?.total_entities ?? 0, icon: Shield, color: "#FFC857", gradient: "linear-gradient(135deg, rgba(255,200,87,0.12), rgba(255,200,87,0.04))" },
    { key: "documents_processed", label: "Successful Scans", value: stats?.documents_processed ?? 0, icon: CheckCircle2, color: "#41E98A", gradient: "linear-gradient(135deg, rgba(65,233,138,0.12), rgba(65,233,138,0.04))" },
  ];

  return (
    <div className="space-y-10 animate-fade-in">
      {/* ── Hero Header ──────────────────────────────────── */}
      <div className="relative">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#AEB6C4]/40 mb-3">Command Center</p>
            <h1 className="text-display text-4xl lg:text-5xl">
              Document <span className="gradient-text-ai">Intelligence</span>
            </h1>
            <p className="text-[#AEB6C4]/60 mt-3 text-base font-light max-w-lg">
              Real-time overview of your AI-powered document processing pipeline
            </p>
          </div>
          <div className="hidden lg:flex items-center gap-2.5 px-4 py-2.5 rounded-2xl"
               style={{ background: 'rgba(65,233,138,0.06)', border: '1px solid rgba(65,233,138,0.1)' }}>
            <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" style={{ boxShadow: '0 0 8px rgba(65,233,138,0.5)' }} />
            <span className="text-xs font-semibold text-accent-success tracking-wide">System Online</span>
          </div>
        </div>
      </div>

      {/* ── Stat Cards ───────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {statIcons.map((item, i) => (
          <div key={item.key} className="stat-card animate-slide-up" style={{ animationDelay: `${i * 0.08}s` }}>
            <div className="flex items-start justify-between mb-5">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center"
                   style={{ background: item.gradient, border: `1px solid ${item.color}15` }}>
                <item.icon className="w-5 h-5" style={{ color: item.color }} />
              </div>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/[0.04] transition-colors cursor-pointer"
                   style={{ border: '1px solid rgba(255,255,255,0.04)' }}>
                <ArrowUpRight className="w-3.5 h-3.5 text-[#AEB6C4]/30" />
              </div>
            </div>
            <div>
              <p className="text-display text-4xl font-bold tracking-tight">
                {isLoading ? (
                  <span className="inline-block w-16 h-9 rounded-lg animate-pulse"
                        style={{ background: 'rgba(255,255,255,0.04)' }} />
                ) : (
                  item.value.toLocaleString()
                )}
              </p>
              <p className="text-[11px] text-[#AEB6C4]/50 mt-2 font-semibold uppercase tracking-[0.15em]">{item.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Content Grid ─────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Risk Distribution */}
        <div className="glass-card p-7">
          <div className="flex items-center gap-3 mb-7">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'rgba(255,92,122,0.08)', border: '1px solid rgba(255,92,122,0.1)' }}>
              <ShieldAlert className="w-5 h-5" style={{ color: '#FF5C7A' }} />
            </div>
            <div>
              <h2 className="text-base font-display font-bold tracking-tight">Risk Analysis</h2>
              <p className="text-[10px] text-[#AEB6C4]/40 uppercase tracking-wider font-medium mt-0.5">Distribution</p>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-5">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="space-y-2.5">
                  <div className="h-3 rounded animate-pulse w-1/4" style={{ background: 'rgba(255,255,255,0.04)' }} />
                  <div className="h-2 rounded-full animate-pulse" style={{ background: 'rgba(255,255,255,0.04)' }} />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-5">
              {Object.entries(stats?.risk_distribution || {}).map(([level, count]) => {
                const colors: Record<string, string> = {
                  CRITICAL: "#FF5C7A",
                  HIGH: "#FFC857",
                  MEDIUM: "#4F7CFF",
                  LOW: "#41E98A",
                };
                const total = Object.values(stats?.risk_distribution || {}).reduce((a: any, b: any) => a + b, 0) as number || 1;
                const percentage = Math.round(((count as number) / total) * 100);
                const barColor = colors[level] || "#4F7CFF";

                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-2.5">
                      <span className="text-[#AEB6C4]/60 font-semibold tracking-wide uppercase text-[10px]">{level}</span>
                      <span className="font-bold tabular-nums" style={{ color: barColor }}>
                        {count as number} <span className="text-[#AEB6C4]/30 font-normal">({percentage}%)</span>
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
                      <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{ width: `${percentage}%`, background: barColor, boxShadow: `0 0 12px ${barColor}30` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Activity Log */}
        <div className="glass-card p-7">
          <div className="flex items-center gap-3 mb-7">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'rgba(79,124,255,0.08)', border: '1px solid rgba(79,124,255,0.1)' }}>
              <Activity className="w-5 h-5 text-brand-500" />
            </div>
            <div>
              <h2 className="text-base font-display font-bold tracking-tight">Activity</h2>
              <p className="text-[10px] text-[#AEB6C4]/40 uppercase tracking-wider font-medium mt-0.5">Recent</p>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-10 rounded-xl animate-pulse" style={{ background: 'rgba(255,255,255,0.04)' }} />
              ))}
            </div>
          ) : activity.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Activity className="w-8 h-8 text-[#AEB6C4]/10 mb-3" />
              <p className="text-sm text-[#AEB6C4]/30 font-medium">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-[300px] overflow-y-auto">
              {activity.map((act: any, idx: number) => (
                <div key={idx} className="flex items-start gap-3.5 p-2.5 rounded-xl hover:bg-white/[0.02] transition-colors">
                  <div className="w-1.5 h-1.5 rounded-full mt-2 shrink-0"
                       style={{ background: '#4F7CFF', boxShadow: '0 0 8px rgba(79,124,255,0.4)' }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{act.title}</p>
                    <p className="text-xs text-[#AEB6C4]/40 truncate mt-0.5">{act.action}</p>
                  </div>
                  <span className="text-[10px] text-[#AEB6C4]/30 shrink-0 font-medium mt-0.5 tabular-nums">
                    {formatDate(act.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Languages */}
        <div className="glass-card p-7">
          <div className="flex items-center gap-3 mb-7">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'rgba(0,225,199,0.08)', border: '1px solid rgba(0,225,199,0.1)' }}>
              <Globe className="w-5 h-5" style={{ color: '#00E1C7' }} />
            </div>
            <div>
              <h2 className="text-base font-display font-bold tracking-tight">Languages</h2>
              <p className="text-[10px] text-[#AEB6C4]/40 uppercase tracking-wider font-medium mt-0.5">Detected</p>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 rounded-xl animate-pulse" style={{ background: 'rgba(255,255,255,0.04)' }} />
              ))}
            </div>
          ) : Object.keys(stats?.language_distribution || {}).length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Globe className="w-8 h-8 text-[#AEB6C4]/10 mb-3" />
              <p className="text-sm text-[#AEB6C4]/30 font-medium">No language data yet</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {Object.entries(stats?.language_distribution || {}).map(([lang, count]) => {
                const total = Object.values(stats?.language_distribution || {}).reduce((a: any, b: any) => a + b, 0) as number || 1;
                const percentage = Math.round(((count as number) / total) * 100);
                return (
                  <div key={lang} className="flex items-center justify-between p-3 rounded-xl transition-colors hover:bg-white/[0.02]"
                       style={{ border: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="text-sm font-semibold">{lang}</span>
                    <span className="text-[11px] font-bold px-3 py-1 rounded-full tabular-nums"
                          style={{ background: 'rgba(0,225,199,0.08)', color: '#00E1C7', border: '1px solid rgba(0,225,199,0.1)' }}>
                      {count as number} ({percentage}%)
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Processing Timeline ───────────────────────────── */}
      <div className="glass-card p-7">
        <div className="flex items-center justify-between mb-7">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'rgba(215,255,126,0.08)', border: '1px solid rgba(215,255,126,0.1)' }}>
              <Terminal className="w-5 h-5" style={{ color: '#D7FF7E' }} />
            </div>
            <div>
              <h2 className="text-base font-display font-bold tracking-tight">Processing Pipeline</h2>
              <p className="text-[10px] text-[#AEB6C4]/40 uppercase tracking-wider font-medium mt-0.5">Intelligence Jobs</p>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: 'rgba(255,255,255,0.03)' }} />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Terminal className="w-8 h-8 text-[#AEB6C4]/10 mb-3" />
            <p className="text-sm text-[#AEB6C4]/30 font-medium">No processing jobs yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-[0.15em] font-semibold"
                    style={{ color: 'rgba(174,182,196,0.35)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <th className="pb-4 pl-4 font-semibold">Document</th>
                  <th className="pb-4 font-semibold">Job Type</th>
                  <th className="pb-4 font-semibold">Status</th>
                  <th className="pb-4 font-semibold">Progress</th>
                  <th className="pb-4 pr-4 font-semibold">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {recentJobs.map((job: any) => (
                  <tr key={job.id} className="table-row group">
                    <td className="py-4 pl-4 font-semibold text-sm">{job.document_title}</td>
                    <td className="py-4">
                      <span className="text-xs font-mono px-2.5 py-1 rounded-lg"
                            style={{ background: 'rgba(255,255,255,0.03)', color: '#AEB6C4' }}>
                        {job.job_type}
                      </span>
                    </td>
                    <td className="py-4">
                      <span className={`badge ${
                        job.status === "COMPLETED" ? "badge-success" :
                        job.status === "FAILED" ? "badge-danger" :
                        "badge-warning"
                      }`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="py-4">
                      <div className="flex items-center gap-3 w-36">
                        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
                          <div className="h-full rounded-full transition-all duration-700 ease-out"
                               style={{
                                 width: `${job.progress}%`,
                                 background: 'linear-gradient(90deg, #4F7CFF, #00E1C7)',
                                 boxShadow: '0 0 8px rgba(79,124,255,0.3)',
                               }} />
                        </div>
                        <span className="text-xs font-bold tabular-nums text-[#AEB6C4]/50 w-8 text-right">{job.progress}%</span>
                      </div>
                    </td>
                    <td className="py-4 pr-4 text-xs text-[#AEB6C4]/40 font-medium tabular-nums">
                      {formatDate(job.timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
