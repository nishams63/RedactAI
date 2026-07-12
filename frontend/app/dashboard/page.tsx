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
    { key: "total_documents", label: "Total Documents", value: stats?.total_documents ?? 0, icon: FileText, color: "from-brand-500 to-blue-600", bg: "bg-brand-500/10", text: "text-brand-500" },
    { key: "total_pages", label: "Pages Processed", value: stats?.total_pages ?? 0, icon: Globe, color: "from-violet-500 to-purple-600", bg: "bg-violet-500/10", text: "text-violet-500" },
    { key: "total_entities", label: "Entities Flagged", value: stats?.total_entities ?? 0, icon: Shield, color: "from-amber-500 to-orange-600", bg: "bg-amber-500/10", text: "text-amber-500" },
    { key: "documents_processed", label: "Successful Scans", value: stats?.documents_processed ?? 0, icon: CheckCircle2, color: "from-emerald-500 to-green-600", bg: "bg-emerald-500/10", text: "text-emerald-500" },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-[rgb(var(--text-secondary))] mt-1">Overview of your document intelligence layer</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {statIcons.map((item, i) => (
          <div key={item.key} className="stat-card animate-slide-up" style={{ animationDelay: `${i * 0.1}s` }}>
            <div className="flex items-start justify-between mb-4">
              <div className={`w-12 h-12 ${item.bg} rounded-xl flex items-center justify-center`}>
                <item.icon className={`w-6 h-6 ${item.text}`} />
              </div>
              <div className={`w-8 h-8 bg-[rgb(var(--bg-secondary))] rounded-lg flex items-center justify-center`}>
                <ArrowUpRight className="w-4 h-4 text-[rgb(var(--text-secondary))]" />
              </div>
            </div>
            <div>
              <p className="text-3xl font-bold">
                {isLoading ? (
                  <span className="inline-block w-16 h-8 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
                ) : (
                  item.value
                )}
              </p>
              <p className="text-sm text-[rgb(var(--text-secondary))] mt-1 font-medium">{item.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Risk Distribution Widget */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-red-500" />
            </div>
            <h2 className="text-lg font-bold">Risk Profile Analysis</h2>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse w-1/4" />
                  <div className="h-2.5 bg-[rgb(var(--bg-secondary))] rounded-full animate-pulse" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-5">
              {Object.entries(stats?.risk_distribution || {}).map(([level, count]) => {
                const colors: Record<string, string> = {
                  CRITICAL: "from-red-600 to-red-500",
                  HIGH: "from-orange-500 to-orange-400",
                  MEDIUM: "from-amber-500 to-amber-400",
                  LOW: "from-emerald-500 to-emerald-400",
                };
                const total = Object.values(stats?.risk_distribution || {}).reduce((a: any, b: any) => a + b, 0) as number || 1;
                const percentage = Math.round(((count as number) / total) * 100);

                return (
                  <div key={level}>
                    <div className="flex justify-between text-sm mb-2 font-medium">
                      <span className="text-[rgb(var(--text-secondary))] tracking-wide">{level}</span>
                      <span>
                        {count as number} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${colors[level] || "from-brand-500 to-blue-500"} rounded-full transition-all duration-1000`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Activity Logs */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-brand-500/10 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-brand-500" />
            </div>
            <h2 className="text-lg font-bold">Activity Log</h2>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-10 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
              ))}
            </div>
          ) : activity.length === 0 ? (
            <p className="text-center py-12 text-sm text-[rgb(var(--text-secondary))]">No recent activity logs.</p>
          ) : (
            <div className="space-y-3.5 max-h-[300px] overflow-y-auto pl-1">
              {activity.map((act: any, idx: number) => (
                <div key={idx} className="flex items-start gap-3.5">
                  <span className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{act.title}</p>
                    <p className="text-xs text-[rgb(var(--text-secondary))] truncate">{act.action}</p>
                  </div>
                  <span className="text-[10px] text-[rgb(var(--text-secondary))] shrink-0 font-medium mt-0.5">
                    {formatDate(act.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Language Distribution Widget */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-violet-500/10 rounded-xl flex items-center justify-center">
              <Globe className="w-5 h-5 text-violet-500" />
            </div>
            <h2 className="text-lg font-bold">Languages Detected</h2>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-8 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
              ))}
            </div>
          ) : Object.keys(stats?.language_distribution || {}).length === 0 ? (
            <p className="text-center py-12 text-sm text-[rgb(var(--text-secondary))]">No language data compiled yet.</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(stats?.language_distribution || {}).map(([lang, count]) => {
                const total = Object.values(stats?.language_distribution || {}).reduce((a: any, b: any) => a + b, 0) as number || 1;
                const percentage = Math.round(((count as number) / total) * 100);
                return (
                  <div key={lang} className="flex items-center justify-between p-2 rounded-xl bg-[rgb(var(--bg-secondary))]/30 border border-[rgb(var(--border-color))]/30">
                    <span className="text-sm font-semibold pl-2">{lang}</span>
                    <span className="text-xs bg-violet-500/10 text-violet-400 px-3 py-1 rounded-full font-bold">
                      {count as number} doc ({percentage}%)
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Recent AI Processing Jobs Timeline */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center">
            <Terminal className="w-5 h-5 text-amber-500" />
          </div>
          <h2 className="text-lg font-bold">Document Intelligence Jobs</h2>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <p className="text-center py-12 text-sm text-[rgb(var(--text-secondary))]">No processing jobs run yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b border-[rgb(var(--border-color))]/50 text-[rgb(var(--text-secondary))] font-bold text-xs uppercase tracking-wider">
                  <th className="pb-3 pl-4">Document</th>
                  <th className="pb-3">Job Type</th>
                  <th className="pb-3">Task Status</th>
                  <th className="pb-3">Progress</th>
                  <th className="pb-3 pr-4">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgb(var(--border-color))]/40">
                {recentJobs.map((job: any) => (
                  <tr key={job.id} className="hover:bg-[rgb(var(--bg-secondary))]/35 transition-colors">
                    <td className="py-3.5 pl-4 font-semibold">{job.document_title}</td>
                    <td className="py-3.5 text-xs font-mono">{job.job_type}</td>
                    <td className="py-3.5">
                      <span className={`badge uppercase text-[10px] font-extrabold ${
                        job.status === "COMPLETED" ? "badge-success" :
                        job.status === "FAILED" ? "badge-danger" :
                        "badge-warning"
                      }`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="py-3.5">
                      <div className="flex items-center gap-3 w-32">
                        <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                          <div className="h-full bg-brand-500 rounded-full transition-all duration-500" style={{ width: `${job.progress}%` }} />
                        </div>
                        <span className="text-xs font-bold shrink-0">{job.progress}%</span>
                      </div>
                    </td>
                    <td className="py-3.5 pr-4 text-xs text-[rgb(var(--text-secondary))] font-medium">
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
