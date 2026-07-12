"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import {
  Zap, Database, Cpu, Activity, Clock, RefreshCw, Play,
  AlertOctagon, CheckCircle2, ChevronRight, BarChart2, Layers
} from "lucide-react";

export default function PerformanceDashboardPage() {
  const queryClient = useQueryClient();
  const [concurrency, setConcurrency] = useState(10);
  const [activeTab, setActiveTab] = useState<"dashboard" | "benchmarks">("dashboard");

  // Queries
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ["performance_stats"],
    queryFn: () => apiClient.getPerformanceStats(),
    refetchInterval: 5000 // Poll every 5 seconds for real-time dashboard updates
  });

  const { data: benchmarksData, isLoading: benchmarksLoading, refetch: refetchBenchmarks } = useQuery({
    queryKey: ["performance_benchmarks"],
    queryFn: () => apiClient.getHistoricalBenchmarks()
  });

  // Mutation
  const runBenchmarkMutation = useMutation({
    mutationFn: (workers: number) => apiClient.runPerformanceBenchmark(workers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["performance_stats"] });
      queryClient.invalidateQueries({ queryKey: ["performance_benchmarks"] });
    }
  });

  const handleRunLoadTest = () => {
    runBenchmarkMutation.mutate(concurrency);
  };

  const cacheItems = stats?.cache ? Object.entries(stats.cache) : [];
  const queue = stats?.queue || {};
  const system = stats?.system || {};
  const stageLatencies = stats?.stage_latencies_ms || {};
  const history = benchmarksData?.history || [];
  const latestRun = history[0] || {};

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Performance & Scalability Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Monitor real-time caching, asynchronous job queue utilization, server hardware telemetry, and track regression benchmarks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchStats();
              refetchBenchmarks();
            }}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-750 transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`px-4 py-2 border-b-2 font-medium text-sm transition-all ${
            activeTab === "dashboard"
              ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          Real-time Telemetry
        </button>
        <button
          onClick={() => setActiveTab("benchmarks")}
          className={`px-4 py-2 border-b-2 font-medium text-sm transition-all ${
            activeTab === "benchmarks"
              ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          }`}
        >
          Load Test Benchmarks ({history.length})
        </button>
      </div>

      {activeTab === "dashboard" ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-start gap-4">
              <div className="p-3 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <span className="text-sm text-slate-500 dark:text-slate-400">CPU Load</span>
                <h3 className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{system.cpu_percent ?? 0} %</h3>
                <div className="w-24 bg-slate-100 dark:bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-blue-600 dark:bg-blue-400 h-1.5"
                    style={{ width: `${system.cpu_percent ?? 0}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-start gap-4">
              <div className="p-3 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <span className="text-sm text-slate-500 dark:text-slate-400">RAM Load</span>
                <h3 className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{system.ram_percent ?? 0} %</h3>
                <div className="w-24 bg-slate-100 dark:bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-indigo-600 dark:bg-indigo-400 h-1.5"
                    style={{ width: `${system.ram_percent ?? 0}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-start gap-4">
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-lg">
                <Database className="h-6 w-6" />
              </div>
              <div>
                <span className="text-sm text-slate-500 dark:text-slate-400">Active Queue Jobs</span>
                <h3 className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{queue.queue_length ?? 0}</h3>
                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                  {queue.active_workers ?? 0} workers busy
                </span>
              </div>
            </div>

            <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-start gap-4">
              <div className="p-3 bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-lg">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <span className="text-sm text-slate-500 dark:text-slate-400">API p95 Latency</span>
                <h3 className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">
                  {stats?.api_p95_ms ?? 0} <span className="text-sm font-normal text-slate-500">ms</span>
                </h3>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  p50: {stats?.api_p50_ms ?? 0} ms
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cache Statistics table */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Enterprise Central Cache stats</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500">
                      <th className="pb-3 font-semibold">Cache Scope</th>
                      <th className="pb-3 font-semibold">Item Count</th>
                      <th className="pb-3 font-semibold text-center">Hits</th>
                      <th className="pb-3 font-semibold text-center">Misses</th>
                      <th className="pb-3 font-semibold text-right">Hit Ratio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cacheItems.map(([key, cacheStats]: [string, any]) => (
                      <tr key={key} className="border-b border-slate-100 dark:border-slate-750 text-slate-700 dark:text-slate-200">
                        <td className="py-3.5 font-medium capitalize">{key.replace("_", " ")}</td>
                        <td className="py-3.5">{cacheStats.item_count} items</td>
                        <td className="py-3.5 text-center text-emerald-600 font-semibold">{cacheStats.hits}</td>
                        <td className="py-3.5 text-center text-amber-600 font-semibold">{cacheStats.misses}</td>
                        <td className="py-3.5 text-right font-bold text-slate-900 dark:text-white">
                          <div className="flex items-center justify-end gap-2">
                            <span>{Math.round(cacheStats.hit_rate * 100)} %</span>
                            <div className="w-16 bg-slate-100 dark:bg-slate-700 h-2 rounded-full overflow-hidden inline-block">
                              <div
                                className="bg-emerald-500 h-2"
                                style={{ width: `${cacheStats.hit_rate * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Queue Monitor Stats */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm flex flex-col justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Task Queue Monitoring</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                    <span className="text-slate-500 text-sm">Worker Utilization</span>
                    <span className="font-semibold text-slate-900 dark:text-white">{queue.worker_utilization ?? 0}%</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                    <span className="text-slate-500 text-sm">Estimated Wait Time</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {Math.round(queue.wait_time_ms ?? 0)} ms
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                    <span className="text-slate-500 text-sm">Total Retries</span>
                    <span className="font-semibold text-amber-600">{queue.retry_count ?? 0}</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-slate-500 text-sm">Failed Jobs</span>
                    <span className="font-semibold text-red-600">{queue.failed_jobs ?? 0}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-350">Queue Telemetry State</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Database queue listener queries jobs every 5 seconds. Celery is operating in eager processing mode locally.
                </p>
              </div>
            </div>
          </div>

          {/* Timing Breakdown and Load Testing Action */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Latency stages */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Pipeline Latency Breakdown (Recent Tasks)</h2>
              <div className="space-y-4">
                {Object.entries(stageLatencies).map(([stage, latency]: [string, any]) => (
                  <div key={stage} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-semibold capitalize text-slate-700 dark:text-slate-200">
                        {stage.replace("_", " ")}
                      </span>
                      <span className="text-slate-500">{latency} ms</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 h-3 rounded-full overflow-hidden">
                      <div
                        className="bg-indigo-600 h-3"
                        style={{ width: `${Math.min(100, (latency / (stats?.api_p50_ms || 2000)) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Launch load test benchmark */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm flex flex-col justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Execute Load test & Regression check</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                  Simulate concurrent legal analysis requests over the benchmark QA suite to trigger regression and improvement comparisons.
                </p>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-slate-750 dark:text-slate-300 block mb-2">
                      Concurrency Load: <span className="text-blue-600">{concurrency} workers</span>
                    </label>
                    <select
                      value={concurrency}
                      onChange={(e) => setConcurrency(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    >
                      <option value={10}>10 Concurrent Workers</option>
                      <option value={25}>25 Concurrent Workers</option>
                      <option value={50}>50 Concurrent Workers</option>
                      <option value={100}>100 Concurrent Workers</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="mt-8">
                <button
                  onClick={handleRunLoadTest}
                  disabled={runBenchmarkMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold disabled:opacity-50 transition"
                >
                  {runBenchmarkMutation.isPending ? (
                    <>
                      <RefreshCw className="h-5 w-5 animate-spin" />
                      Running Benchmark...
                    </>
                  ) : (
                    <>
                      <Play className="h-5 w-5" />
                      Launch Load Test
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        /* Benchmarks tab view */
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Historical Regression Runs</h2>
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-500">
                Total Runs recorded: {history.length}
              </span>
            </div>
          </div>

          <div className="space-y-6">
            {history.map((run: any) => {
              const hasRegressions = run.regressions && Object.keys(run.regressions).length > 0;
              const hasImprovements = run.improvements && Object.keys(run.improvements).length > 0;
              
              let statusLabel = "UNCHANGED";
              let statusClass = "bg-slate-100 text-slate-700";
              
              if (hasRegressions) {
                statusLabel = "REGRESSED";
                statusClass = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
              } else if (hasImprovements) {
                statusLabel = "IMPROVED";
                statusClass = "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
              }

              return (
                <div key={run.id} className="p-6 border border-slate-200 dark:border-slate-700 rounded-xl space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-700 pb-3">
                    <div>
                      <span className="text-xs text-slate-500 font-medium block">
                        Timestamp: {new Date(run.created_at).toLocaleString()}
                      </span>
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">
                        Run ID: {run.id}
                      </span>
                    </div>
                    <span className={`px-3 py-1.5 text-xs font-bold rounded-full ${statusClass}`}>
                      {statusLabel}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500 block">Concurrency</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.concurrency} threads</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Throughput</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.throughput} req/s</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Avg Latency</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.avg_latency} ms</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Peak Latency</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.peak_latency} ms</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Avg CPU</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.cpu_util}%</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Avg RAM</span>
                      <span className="font-semibold text-slate-900 dark:text-white">{run.ram_util}%</span>
                    </div>
                  </div>

                  {/* Reports list */}
                  {(hasImprovements || hasRegressions) && (
                    <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2 text-sm">
                      {hasImprovements && (
                        <div className="space-y-1">
                          <span className="font-bold text-emerald-600">Improvements Report:</span>
                          {Object.entries(run.improvements).map(([metric, detail]: [string, any]) => (
                            <p key={metric} className="text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                              <CheckCircle2 className="h-4 w-4 text-emerald-500 inline shrink-0" />
                              {detail.message}
                            </p>
                          ))}
                        </div>
                      )}
                      {hasRegressions && (
                        <div className="space-y-1">
                          <span className="font-bold text-red-600">Regressions Report:</span>
                          {Object.entries(run.regressions).map(([metric, detail]: [string, any]) => (
                            <p key={metric} className="text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                              <AlertOctagon className="h-4 w-4 text-red-500 inline shrink-0" />
                              {detail.message}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
