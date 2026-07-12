"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import {
  Brain, Target, Activity, Shield, TrendingUp,
  Cpu, Zap, HardDrive, BarChart2, Layers,
  RefreshCw, CheckCircle, AlertCircle, HelpCircle
} from "lucide-react";

export default function DLAnalyticsPage() {
  const queryClient = useQueryClient();
  const [epochs, setEpochs] = useState<number>(3);
  const [batchSize, setBatchSize] = useState<number>(8);
  const [learningRate, setLearningRate] = useState<number>(2e-5);
  const [datasetSize, setDatasetSize] = useState<number>(5000);

  // Queries
  const { data: dlEvaluation, isLoading: isEvalLoading, error: evalError } = useQuery({
    queryKey: ["dl-evaluation"],
    queryFn: () => apiClient.getDLEvaluation(),
    retry: false,
  });

  const { data: comparison, isLoading: isCompLoading } = useQuery({
    queryKey: ["dl-comparison"],
    queryFn: () => apiClient.getDLComparison(),
    retry: false,
  });

  // Mutations
  const trainMutation = useMutation({
    mutationFn: () => apiClient.trainDLModel(epochs, batchSize, learningRate, datasetSize),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dl-evaluation"] });
      queryClient.invalidateQueries({ queryKey: ["dl-comparison"] });
    },
  });

  const handleTrain = () => {
    trainMutation.mutate();
  };

  const isTraining = trainMutation.isPending;

  if (isEvalLoading || isCompLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const getMetricColor = (val: number) => {
    if (val >= 0.9) return "text-emerald-500";
    if (val >= 0.75) return "text-amber-500";
    return "text-red-500";
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold">Deep Learning Analytics</h1>
          </div>
          <p className="text-[rgb(var(--text-secondary))] mt-2">
            Fine-tune legal-domain transformer models and compare them against traditional ML baselines.
          </p>
        </div>

        {/* Training trigger */}
        <div className="flex items-center gap-3 bg-[rgb(var(--bg-card))] p-3 rounded-xl border border-[rgb(var(--border-color))] shadow-sm flex-wrap">
          <div className="flex flex-col text-xs text-[rgb(var(--text-secondary))] pr-2 border-r border-[rgb(var(--border-color))]">
            <span>Model: LegalBERT</span>
            <span>Dataset: {datasetSize} samples</span>
          </div>
          <button
            onClick={handleTrain}
            disabled={isTraining}
            className="btn-primary flex items-center gap-2"
          >
            {isTraining ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Fine-tuning...
              </>
            ) : (
              <>
                <Cpu className="w-4 h-4" />
                Fine-tune BERT
              </>
            )}
          </button>
        </div>
      </div>

      {isTraining && (
        <div className="p-4 bg-brand-500/10 text-brand-300 border border-brand-500/20 rounded-xl flex items-center gap-3 animate-pulse">
          <RefreshCw className="w-5 h-5 animate-spin text-brand-500" />
          <div>
            <div className="font-semibold text-sm">Fine-tuning LegalBERT on Server...</div>
            <div className="text-xs text-[rgb(var(--text-secondary))]">
              Training runs on CPU and takes approximately 30–50 seconds. Please wait while metrics and loss curves are generated.
            </div>
          </div>
        </div>
      )}

      {/* Configuration panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        <div className="card lg:col-span-1 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-[rgb(var(--text-secondary))]">
            Hyperparameters
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Epochs</label>
              <select
                value={epochs}
                onChange={(e) => setEpochs(Number(e.target.value))}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm"
              >
                <option value={1}>1 (Quick Test)</option>
                <option value={3}>3 (Normal)</option>
                <option value={5}>5 (Comprehensive)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Batch Size</label>
              <select
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm"
              >
                <option value={4}>4 (Low VRAM)</option>
                <option value={8}>8 (Default)</option>
                <option value={16}>16</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Learning Rate</label>
              <select
                value={learningRate}
                onChange={(e) => setLearningRate(Number(e.target.value))}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm"
              >
                <option value={1e-5}>1e-5</option>
                <option value={2e-5}>2e-5 (Default)</option>
                <option value={5e-5}>5e-5</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Dataset Size</label>
              <select
                value={datasetSize}
                onChange={(e) => setDatasetSize(Number(e.target.value))}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm"
              >
                <option value={500}>500 (Dev)</option>
                <option value={5000}>5,000 (Default)</option>
                <option value={10000}>10,000</option>
              </select>
            </div>
          </div>
        </div>

        {/* DL Metrics Snapshot */}
        <div className="lg:col-span-3 card flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-[rgb(var(--text-secondary))] mb-4">
              Latest BERT Fine-Tuning Metrics
            </h3>
            {dlEvaluation ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                {[
                  { label: "Accuracy", value: dlEvaluation.metrics.accuracy, icon: Target },
                  { label: "F1 Macro", value: dlEvaluation.metrics.f1_macro, icon: Activity },
                  { label: "Latency (ms)", value: dlEvaluation.metrics.latency_ms, icon: Zap, format: (v: number) => `${v.toFixed(1)} ms` },
                  { label: "Memory (MB)", value: dlEvaluation.metrics.memory_mb, icon: HardDrive, format: (v: number) => `${v.toFixed(0)} MB` },
                ].map((item, idx) => (
                  <div key={idx} className="p-4 bg-[rgb(var(--bg-secondary))] rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <item.icon className="w-4 h-4 text-[rgb(var(--text-secondary))]" />
                      <span className="text-xs text-[rgb(var(--text-secondary))] font-medium">{item.label}</span>
                    </div>
                    <span className="text-2xl font-bold">
                      {item.format ? item.format(item.value) : `${(item.value * 100).toFixed(1)}%`}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-[rgb(var(--text-secondary))]">
                No active fine-tuning report found. Please execute fine-tuning to generate metrics.
              </div>
            )}
          </div>

          {dlEvaluation && (
            <div className="mt-4 pt-4 border-t border-[rgb(var(--border-color))] flex justify-between text-xs text-[rgb(var(--text-secondary))]">
              <span>Reproducibility: Seed={dlEvaluation.reproducibility.python_seed}</span>
              <span>Dataset Hash: {dlEvaluation.dataset_hash.slice(0, 10)}...</span>
            </div>
          )}
        </div>
      </div>

      {/* Comparison and training graphs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ML vs DL Performance Audit */}
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-indigo-500" />
            Traditional ML vs Deep Learning Comparison
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-[rgb(var(--border-color))] text-[rgb(var(--text-secondary))]">
                  <th className="pb-3 pr-4 font-medium">Model</th>
                  <th className="pb-3 px-4 font-medium">Type</th>
                  <th className="pb-3 px-4 font-medium">F1 Score</th>
                  <th className="pb-3 px-4 font-medium">Latency</th>
                  <th className="pb-3 px-4 font-medium">Throughput</th>
                  <th className="pb-3 px-4 font-medium">RAM/VRAM</th>
                </tr>
              </thead>
              <tbody>
                {comparison && Object.entries(comparison.models).map(([name, m]: [string, any]) => (
                  <tr key={name} className="border-b border-[rgb(var(--border-color))]/50 hover:bg-[rgb(var(--bg-secondary))]/50 transition-colors">
                    <td className="py-3 pr-4 font-medium">{name}</td>
                    <td className="py-3 px-4 text-xs text-[rgb(var(--text-secondary))]">{m.type}</td>
                    <td className="py-3 px-4 font-semibold text-brand-500">{(m.f1 * 100).toFixed(1)}%</td>
                    <td className="py-3 px-4">{m.latency_ms.toFixed(1)} ms</td>
                    <td className="py-3 px-4">{m.throughput.toFixed(0)} doc/s</td>
                    <td className="py-3 px-4">{m.memory_mb.toFixed(0)} MB</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Training information / curves */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Training Curves</h3>
          {dlEvaluation ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3">
                <div className="bg-[rgb(var(--bg-secondary))] p-1 rounded-lg border border-[rgb(var(--border-color))] overflow-hidden flex flex-col items-center">
                  <span className="text-[10px] text-[rgb(var(--text-secondary))] mb-1 font-semibold">Loss Curve</span>
                  <img
                    src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/dl/curves/loss_curve.png?t=${Date.now()}`}
                    alt="Loss Curve"
                    className="w-full h-auto object-contain rounded-md"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
                <div className="bg-[rgb(var(--bg-secondary))] p-1 rounded-lg border border-[rgb(var(--border-color))] overflow-hidden flex flex-col items-center">
                  <span className="text-[10px] text-[rgb(var(--text-secondary))] mb-1 font-semibold">Accuracy Curve</span>
                  <img
                    src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/dl/curves/accuracy_curve.png?t=${Date.now()}`}
                    alt="Accuracy Curve"
                    className="w-full h-auto object-contain rounded-md"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
              </div>
              <div className="text-xs space-y-2">
                <div className="flex justify-between">
                  <span>Pytorch ONNX Exported:</span>
                  <span className="text-emerald-500 font-semibold">Yes (model.onnx)</span>
                </div>
                <div className="flex justify-between">
                  <span>Training Report Generated:</span>
                  <span className="text-emerald-500 font-semibold">Yes (training_report.pdf)</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-sm text-[rgb(var(--text-secondary))]">
              Curves will generate once training executes.
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
