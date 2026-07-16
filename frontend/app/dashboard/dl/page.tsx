"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import {
  Brain, Target, Activity, Shield, TrendingUp,
  Cpu, Zap, HardDrive, BarChart2, Layers,
  RefreshCw, CheckCircle, AlertCircle, HelpCircle,
  ArrowUpDown, Check, Play, FileText
} from "lucide-react";

export default function DLAnalyticsPage() {
  const queryClient = useQueryClient();
  const [epochs, setEpochs] = useState<number>(3);
  const [batchSize, setBatchSize] = useState<number>(8);
  const [learningRate, setLearningRate] = useState<number>(2e-5);
  const [datasetSize, setDatasetSize] = useState<number>(5000);
  
  const [modelType, setModelType] = useState<string>("legalbert");
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isDeployPending, setIsDeployPending] = useState(false);
  
  // Sorting State
  const [sortBy, setSortBy] = useState<string>("f1");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Queries
  const { data: dlEvaluation, isLoading: isEvalLoading } = useQuery({
    queryKey: ["dl-evaluation"],
    queryFn: () => apiClient.getDLEvaluation(),
    retry: false,
  });

  const { data: comparison, isLoading: isCompLoading } = useQuery({
    queryKey: ["dl-comparison"],
    queryFn: () => apiClient.getDLComparison(),
    retry: false,
  });

  const { data: registryModels, isLoading: isRegistryLoading } = useQuery({
    queryKey: ["dl-models"],
    queryFn: () => apiClient.getDLModels(),
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.some((m: any) => m.status === "Training" || m.status === "Deploying");
      return hasActiveJob ? 3000 : false;
    }
  });

  const { data: progressData } = useQuery({
    queryKey: ["dl-progress"],
    queryFn: () => apiClient.getDLProgress(),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" && progressData?.status === "Training") {
        queryClient.invalidateQueries({ queryKey: ["dl-evaluation"] });
        queryClient.invalidateQueries({ queryKey: ["dl-comparison"] });
        queryClient.invalidateQueries({ queryKey: ["dl-models"] });
      }
      return status === "Training" ? 1500 : false;
    },
  });

  // Mutations
  const trainMutation = useMutation({
    mutationFn: () => apiClient.trainDLModel(epochs, batchSize, learningRate, datasetSize),
    onSuccess: () => {
      setNotification({ type: "success", message: "LegalBERT fine-tuning pipeline triggered successfully." });
      queryClient.invalidateQueries({ queryKey: ["dl-progress"] });
      queryClient.invalidateQueries({ queryKey: ["dl-models"] });
    },
    onError: (err: any) => {
      setNotification({ type: "error", message: `Failed to start training: ${err.message || err}` });
    }
  });

  const trainSeqMutation = useMutation({
    mutationFn: () => apiClient.trainSequenceModel(modelType, datasetSize),
    onSuccess: () => {
      setNotification({ type: "success", message: `${modelType.toUpperCase()} training pipeline triggered successfully.` });
      queryClient.invalidateQueries({ queryKey: ["dl-progress"] });
      queryClient.invalidateQueries({ queryKey: ["dl-models"] });
    },
    onError: (err: any) => {
      setNotification({ type: "error", message: `Failed to start training: ${err.message || err}` });
    }
  });

  const handleTrain = () => {
    setNotification(null);
    if (modelType === "legalbert") {
      trainMutation.mutate();
    } else {
      trainSeqMutation.mutate();
    }
  };

  const handleDeploy = async (modelId: string) => {
    setIsDeployPending(true);
    setNotification(null);
    try {
      await apiClient.request<any>(`/dl/registry/deploy?model_id=${modelId}`, {
        method: "POST",
      });
      setNotification({ type: "success", message: "Model deployment triggered successfully." });
      queryClient.invalidateQueries({ queryKey: ["dl-models"] });
      queryClient.invalidateQueries({ queryKey: ["dl-comparison"] });
    } catch (err: any) {
      setNotification({ type: "error", message: `Deployment failed: ${err.message || err}` });
    } finally {
      setIsDeployPending(false);
    }
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  };

  const isTraining = trainMutation.isPending || trainSeqMutation.isPending || progressData?.status === "Training";

  if (isEvalLoading || isCompLoading || isRegistryLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const sortedModels = comparison?.models ? Object.entries(comparison.models).sort((a: any, b: any) => {
    const valA = a[1][sortBy] ?? 0;
    const valB = b[1][sortBy] ?? 0;
    if (sortBy === "model") {
      return sortOrder === "asc" ? a[0].localeCompare(b[0]) : b[0].localeCompare(a[0]);
    }
    return sortOrder === "asc" ? valA - valB : valB - valA;
  }) : [];

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "Training":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20 animate-pulse">Training</span>;
      case "Ready":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-500/10 text-blue-500 border border-blue-500/20">Ready</span>;
      case "Deploying":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-500/10 text-purple-500 border border-purple-500/20 animate-pulse">Deploying</span>;
      case "Active":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1 w-max"><CheckCircle className="w-3.5 h-3.5" /> Active</span>;
      case "Deprecated":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-500/10 text-gray-400 border border-gray-500/20">Deprecated</span>;
      case "Failed":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-500/10 text-red-500 border border-red-500/20">Failed</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-500/10 text-gray-500 border border-gray-500/20">{status}</span>;
    }
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
            <h1 className="text-3xl font-bold">Deep Learning Dashboard</h1>
          </div>
          <p className="text-[rgb(var(--text-secondary))] mt-2">
            Fine-tune legal-domain transformer and sequence models and manage model deployments live.
          </p>
        </div>

        {/* Training trigger dropdown */}
        <div className="flex items-center gap-3 bg-[rgb(var(--bg-card))] p-3 rounded-xl border border-[rgb(var(--border-color))] shadow-sm flex-wrap">
          <div className="flex flex-col text-xs text-[rgb(var(--text-secondary))] pr-2 border-r border-[rgb(var(--border-color))]">
            <label className="text-[10px] uppercase font-bold text-[rgb(var(--text-secondary))] block">Select Model</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              disabled={isTraining}
              className="bg-transparent border-none p-0 text-sm font-semibold focus:ring-0 text-[rgb(var(--text-primary))]"
            >
              <option value="legalbert">LegalBERT (Transformer)</option>
              <option value="lstm">LSTM Classifier</option>
              <option value="gru">GRU Classifier</option>
              <option value="rnn">RNN Classifier</option>
              <option value="bilstm">BiLSTM Classifier</option>
            </select>
          </div>
          <button
            onClick={handleTrain}
            disabled={isTraining}
            className="btn-primary flex items-center gap-2"
          >
            {isTraining ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Training Model...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Train Model
              </>
            )}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div className={`p-4 rounded-xl border flex items-center justify-between animate-fade-in ${
          notification.type === "success" 
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" 
            : "bg-red-500/10 border-red-500/20 text-red-500"
        }`}>
          <div className="flex items-center gap-3">
            {notification.type === "success" 
              ? <CheckCircle className="w-5 h-5" /> 
              : <AlertCircle className="w-5 h-5" />}
            <span className="text-sm font-semibold">{notification.message}</span>
          </div>
          <button 
            onClick={() => setNotification(null)}
            className="text-xs font-semibold underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Background Training Progress Tracker */}
      {progressData?.status === "Training" && (
        <div className="card border border-amber-500/20 bg-amber-500/5 space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 animate-spin text-amber-500" />
              <div>
                <h3 className="font-semibold text-amber-500">Model Training in Progress</h3>
                <p className="text-xs text-[rgb(var(--text-secondary))]">
                  Live metrics are being streamed from the server.
                </p>
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs text-[rgb(var(--text-secondary))] block">Est. Time Remaining</span>
              <span className="font-mono text-sm font-bold text-amber-500">
                {progressData.estimated_time_remaining > 0 
                  ? `${Math.round(progressData.estimated_time_remaining)}s`
                  : "Calculating..."}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
            <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
              <span className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Epoch</span>
              <span className="text-lg font-bold">{progressData.current_epoch} / {progressData.total_epochs}</span>
            </div>
            <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
              <span className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Current Loss</span>
              <span className="text-lg font-bold font-mono">{progressData.current_loss.toFixed(4)}</span>
            </div>
            <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
              <span className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Validation Accuracy</span>
              <span className="text-lg font-bold">{progressData.val_accuracy > 0 ? `${(progressData.val_accuracy * 100).toFixed(1)}%` : "N/A"}</span>
            </div>
            <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
              <span className="text-xs text-[rgb(var(--text-secondary))] block mb-1">Status</span>
              <span className="text-lg font-bold text-amber-500">{progressData.status}</span>
            </div>
          </div>

          <div className="w-full bg-[rgb(var(--bg-secondary))] h-2 rounded-full overflow-hidden">
            <div 
              className="bg-amber-500 h-full transition-all duration-500 ease-out"
              style={{ 
                width: `${progressData.total_epochs > 0 ? (progressData.current_epoch / progressData.total_epochs) * 100 : 0}%` 
              }}
            />
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
                disabled={isTraining}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm text-[rgb(var(--text-primary))] disabled:opacity-50"
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
                disabled={isTraining}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm text-[rgb(var(--text-primary))] disabled:opacity-50"
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
                disabled={isTraining}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm text-[rgb(var(--text-primary))] disabled:opacity-50"
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
                disabled={isTraining}
                className="w-full bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm text-[rgb(var(--text-primary))] disabled:opacity-50"
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
                  { label: "Accuracy", value: dlEvaluation.metrics?.accuracy, icon: Target },
                  { label: "F1 Macro", value: dlEvaluation.metrics?.f1_macro, icon: Activity },
                  { label: "Latency (ms)", value: dlEvaluation.metrics?.latency_ms, icon: Zap, format: (v: number) => `${v?.toFixed(1)} ms` },
                  { label: "Memory (MB)", value: dlEvaluation.metrics?.memory_mb, icon: HardDrive, format: (v: number) => `${v?.toFixed(0)} MB` },
                ].map((item, idx) => (
                  <div key={idx} className="p-4 bg-[rgb(var(--bg-secondary))] rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <item.icon className="w-4 h-4 text-[rgb(var(--text-secondary))]" />
                      <span className="text-xs text-[rgb(var(--text-secondary))] font-medium">{item.label}</span>
                    </div>
                    <span className="text-2xl font-bold">
                      {item.value !== undefined ? (item.format ? item.format(item.value) : `${(item.value * 100).toFixed(1)}%`) : "N/A"}
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
              <span>Reproducibility: Seed={dlEvaluation.reproducibility?.python_seed}</span>
              <span>Dataset Hash: {dlEvaluation.dataset_hash?.slice(0, 10)}...</span>
            </div>
          )}
        </div>
      </div>

      {/* Model Comparison Table */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-indigo-500" />
          Model Comparison Matrix
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-[rgb(var(--border-color))] text-[rgb(var(--text-secondary))]">
                {[
                  { label: "Model", field: "model" },
                  { label: "Type", field: "type" },
                  { label: "Accuracy", field: "accuracy" },
                  { label: "Precision", field: "precision" },
                  { label: "Recall", field: "recall" },
                  { label: "F1 Score", field: "f1" },
                  { label: "Latency", field: "latency_ms" },
                  { label: "Throughput", field: "throughput" },
                  { label: "RAM/VRAM", field: "memory_mb" },
                  { label: "Model Size", field: "model_size_mb" },
                  { label: "Training Time", field: "training_time_seconds" },
                  { label: "Inference Time", field: "inference_time_ms" }
                ].map((col) => (
                  <th 
                    key={col.field} 
                    onClick={() => handleSort(col.field)}
                    className="pb-3 px-4 font-medium cursor-pointer hover:text-[rgb(var(--text-primary))] transition-colors select-none first:pl-0"
                  >
                    <div className="flex items-center gap-1.5 whitespace-nowrap">
                      {col.label}
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedModels.map(([name, m]: [string, any]) => (
                <tr key={name} className="border-b border-[rgb(var(--border-color))]/50 hover:bg-[rgb(var(--bg-secondary))]/50 transition-colors">
                  <td className="py-3 pr-4 font-semibold first:pl-0">{name}</td>
                  <td className="py-3 px-4 text-xs text-[rgb(var(--text-secondary))]">{m.type}</td>
                  <td className="py-3 px-4">{(m.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4">{(m.precision * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4">{(m.recall * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 font-bold text-brand-500">{(m.f1 * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4">{m.latency_ms?.toFixed(1)} ms</td>
                  <td className="py-3 px-4">{m.throughput?.toFixed(0)} doc/s</td>
                  <td className="py-3 px-4">{m.memory_mb?.toFixed(0)} MB</td>
                  <td className="py-3 px-4 font-mono text-xs">{m.model_size_mb?.toFixed(1)} MB</td>
                  <td className="py-3 px-4">{m.training_time_seconds?.toFixed(1)}s</td>
                  <td className="py-3 px-4 font-mono text-xs">{m.inference_time_ms?.toFixed(2)} ms</td>
                </tr>
              ))}
              {sortedModels.length === 0 && (
                <tr>
                  <td colSpan={12} className="py-8 text-center text-[rgb(var(--text-secondary))]">
                    No comparison metrics compiled.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Registry List */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-500" />
          Model Registry & Deployments
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-[rgb(var(--border-color))] text-[rgb(var(--text-secondary))]">
                <th className="pb-3 pr-4 font-medium">Model Name</th>
                <th className="pb-3 px-4 font-medium">Version</th>
                <th className="pb-3 px-4 font-medium">Registered Date</th>
                <th className="pb-3 px-4 font-medium">Accuracy</th>
                <th className="pb-3 px-4 font-medium">F1 Score</th>
                <th className="pb-3 px-4 font-medium">Status</th>
                <th className="pb-3 pl-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {registryModels && registryModels.map((model: any) => (
                <tr key={model.id} className="border-b border-[rgb(var(--border-color))]/50 hover:bg-[rgb(var(--bg-secondary))]/50 transition-colors">
                  <td className="py-3 pr-4 font-medium">{model.name}</td>
                  <td className="py-3 px-4 font-mono text-xs">{model.version}</td>
                  <td className="py-3 px-4 text-xs text-[rgb(var(--text-secondary))]">
                    {formatDate(model.created_at)}
                  </td>
                  <td className="py-3 px-4 font-semibold">
                    {model.parameters?.accuracy ? `${(model.parameters.accuracy * 100).toFixed(1)}%` : "N/A"}
                  </td>
                  <td className="py-3 px-4 font-semibold text-brand-500">
                    {model.parameters?.f1_macro ? `${(model.parameters.f1_macro * 100).toFixed(1)}%` : "N/A"}
                  </td>
                  <td className="py-3 px-4">{renderStatusBadge(model.status)}</td>
                  <td className="py-3 pl-4 text-right">
                    {model.status !== "Active" && model.status !== "Training" && model.status !== "Failed" && (
                      <button
                        onClick={() => handleDeploy(model.id)}
                        disabled={isTraining || isDeployPending}
                        className="px-3 py-1 rounded bg-brand-500 hover:bg-brand-600 text-white font-medium disabled:opacity-50 text-xs transition-colors"
                      >
                        Deploy
                      </button>
                    )}
                    {model.status === "Active" && (
                      <span className="text-xs text-emerald-500 font-semibold flex items-center justify-end gap-1"><Check className="w-3.5 h-3.5" /> Live</span>
                    )}
                  </td>
                </tr>
              ))}
              {(!registryModels || registryModels.length === 0) && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[rgb(var(--text-secondary))]">
                    No models registered in the registry.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Training Curves & Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-500" />
            Training Performance Curves
          </h3>
          {dlEvaluation ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[rgb(var(--bg-secondary))] p-2 rounded-xl border border-[rgb(var(--border-color))] flex flex-col items-center">
                <span className="text-xs font-semibold text-[rgb(var(--text-secondary))] mb-2">Loss Minimization</span>
                <img
                  src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/dl/curves/loss_curve.png?t=${Date.now()}`}
                  alt="Loss Curve"
                  className="w-full h-auto object-contain rounded-lg"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
              <div className="bg-[rgb(var(--bg-secondary))] p-2 rounded-xl border border-[rgb(var(--border-color))] flex flex-col items-center">
                <span className="text-xs font-semibold text-[rgb(var(--text-secondary))] mb-2">Accuracy Convergence</span>
                <img
                  src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/dl/curves/accuracy_curve.png?t=${Date.now()}`}
                  alt="Accuracy Curve"
                  className="w-full h-auto object-contain rounded-lg"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-[rgb(var(--text-secondary))]">
              Curves will generate once training executes.
            </div>
          )}
        </div>

        <div className="card flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-4">Export Artifacts</h3>
            <p className="text-xs text-[rgb(var(--text-secondary))] mb-4">
              Export optimized model files, checkpoints, and compiled compliance reports.
            </p>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs font-semibold">Model ONNX Binary</span>
                </div>
                <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded">model.onnx</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-[rgb(var(--bg-secondary))] rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-500" />
                  <span className="text-xs font-semibold">Model Card Card</span>
                </div>
                <span className="text-[10px] font-mono bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded">card.md</span>
              </div>
            </div>
          </div>
          <div className="text-[10px] text-[rgb(var(--text-secondary))] mt-4 pt-4 border-t border-[rgb(var(--border-color))]">
            All artifacts are saved live under the <code className="font-mono bg-[rgb(var(--bg-secondary))] px-1 rounded">/artifacts</code> folder.
          </div>
        </div>
      </div>
    </div>
  );
}
