"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import {
  Brain, Target, Activity, Shield, TrendingUp,
  AlertTriangle, Clock, RefreshCw, BarChart2,
  Database, GitBranch, Layers
} from "lucide-react";

export default function MLAnalyticsPage() {
  const queryClient = useQueryClient();
  const [datasetSize, setDatasetSize] = useState<number>(5000);
  
  // Queries
  const { data: evaluation, isLoading: isEvalLoading } = useQuery({
    queryKey: ["ml-evaluation"],
    queryFn: () => apiClient.getMLEvaluation(),
    retry: false,
  });

  const { data: experiments, isLoading: isExpLoading } = useQuery({
    queryKey: ["ml-experiments"],
    queryFn: () => apiClient.getMLExperiments(5),
  });

  // Mutations
  const trainMutation = useMutation({
    mutationFn: (size: number) => apiClient.trainModel(size),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ml-evaluation"] });
      queryClient.invalidateQueries({ queryKey: ["ml-experiments"] });
    },
  });

  const handleTrain = () => {
    trainMutation.mutate(datasetSize);
  };

  const isTraining = trainMutation.isPending;

  if (isEvalLoading || isExpLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const bestModelKey = evaluation?.best_model;
  const bestModel = bestModelKey ? evaluation.models[bestModelKey] : null;
  const metrics = bestModel?.metrics;

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
              <Brain className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold">ML Analytics</h1>
          </div>
          <p className="text-[rgb(var(--text-secondary))] mt-2">
            Enterprise Machine Learning Pipeline for Document Sensitivity Prediction
          </p>
        </div>

        <div className="flex items-center gap-3 bg-[rgb(var(--bg-card))] p-2 rounded-xl border border-[rgb(var(--border-color))] shadow-sm">
          <select 
            value={datasetSize}
            onChange={(e) => setDatasetSize(Number(e.target.value))}
            disabled={isTraining}
            className="bg-[rgb(var(--bg-secondary))] border-none rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500"
          >
            <option value={500}>500 Samples (Dev)</option>
            <option value={5000}>5,000 Samples (Default)</option>
            <option value={10000}>10,000 Samples (Large)</option>
            <option value={50000}>50,000 Samples (Enterprise)</option>
          </select>
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
                <Database className="w-4 h-4" />
                Train Pipeline
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Content */}
      {evaluation ? (
        <>
          {/* Top Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { label: "Accuracy", value: metrics?.accuracy, icon: Target },
              { label: "F1 Score (Macro)", value: metrics?.f1_macro, icon: Activity },
              { label: "Precision", value: metrics?.precision_macro, icon: Shield },
              { label: "Recall", value: metrics?.recall_macro, icon: TrendingUp },
            ].map((stat, i) => (
              <div key={i} className="stat-card">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-[rgb(var(--bg-secondary))] rounded-lg">
                    <stat.icon className="w-5 h-5 text-[rgb(var(--text-secondary))]" />
                  </div>
                  <h3 className="font-medium text-[rgb(var(--text-secondary))]">{stat.label}</h3>
                </div>
                <div className="flex items-end gap-2 mt-4">
                  <span className={`text-4xl font-bold ${getMetricColor(stat.value || 0)}`}>
                    {((stat.value || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Model Comparison & Confusion Matrix */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Model Comparison Table */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-500" />
                  Algorithm Comparison
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[rgb(var(--border-color))] text-[rgb(var(--text-secondary))] text-sm">
                        <th className="pb-3 pr-4 font-medium">Algorithm</th>
                        <th className="pb-3 px-4 font-medium">F1 Macro</th>
                        <th className="pb-3 px-4 font-medium">Accuracy</th>
                        <th className="pb-3 px-4 font-medium">ROC-AUC</th>
                        <th className="pb-3 px-4 font-medium">Train Time</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {Object.entries(evaluation.models)
                        .sort((a: any, b: any) => b[1].metrics.f1_macro - a[1].metrics.f1_macro)
                        .map(([name, modelData]: [string, any], idx) => (
                        <tr key={name} className="border-b border-[rgb(var(--border-color))]/50 hover:bg-[rgb(var(--bg-secondary))]/50 transition-colors">
                          <td className="py-3 pr-4">
                            <div className="flex items-center gap-2">
                              {name === bestModelKey && (
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                              )}
                              <span className={name === bestModelKey ? "font-semibold text-brand-500" : ""}>{name}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">{(modelData.metrics.f1_macro * 100).toFixed(2)}%</td>
                          <td className="py-3 px-4">{(modelData.metrics.accuracy * 100).toFixed(2)}%</td>
                          <td className="py-3 px-4">{modelData.metrics.roc_auc ? (modelData.metrics.roc_auc * 100).toFixed(2) + "%" : "-"}</td>
                          <td className="py-3 px-4">{modelData.performance.training_time_seconds.toFixed(2)}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Confusion Matrix */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <BarChart2 className="w-5 h-5 text-purple-500" />
                  Confusion Matrix ({bestModelKey})
                </h3>
                <div className="overflow-x-auto">
                  <div className="inline-block min-w-full">
                    <div className="grid grid-cols-5 gap-1 mb-1">
                      <div className="font-medium text-xs text-[rgb(var(--text-secondary))] flex items-end pb-2">True \ Pred</div>
                      {evaluation.dataset_metadata.classes.map((c: string) => (
                        <div key={c} className="text-xs font-medium text-center truncate px-1 text-[rgb(var(--text-secondary))]">{c}</div>
                      ))}
                    </div>
                    {bestModel?.confusion_matrix.map((row: number[], i: number) => (
                      <div key={i} className="grid grid-cols-5 gap-1 mb-1">
                        <div className="text-xs font-medium flex items-center pr-2 truncate text-[rgb(var(--text-secondary))]">
                          {evaluation.dataset_metadata.classes[i]}
                        </div>
                        {row.map((val: number, j: number) => {
                          // Simple heatmap coloring
                          const maxInRow = Math.max(...row);
                          const intensity = maxInRow > 0 ? (val / maxInRow) : 0;
                          const isCorrect = i === j;
                          
                          let bgClass = "bg-[rgb(var(--bg-secondary))]";
                          let textClass = "text-[rgb(var(--text-primary))]";
                          
                          if (val > 0) {
                            if (isCorrect) {
                              if (intensity > 0.8) bgClass = "bg-emerald-500";
                              else if (intensity > 0.4) bgClass = "bg-emerald-500/60";
                              else bgClass = "bg-emerald-500/30";
                              if (intensity > 0.4) textClass = "text-white";
                            } else {
                              if (intensity > 0.5) bgClass = "bg-red-500/80";
                              else if (intensity > 0.2) bgClass = "bg-red-500/40";
                              else bgClass = "bg-red-500/20";
                              if (intensity > 0.5) textClass = "text-white";
                            }
                          }

                          return (
                            <div key={j} className={`h-12 flex items-center justify-center rounded-md text-sm font-medium transition-colors ${bgClass} ${textClass}`}>
                              {val}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </div>

            {/* Right Column: Feature Importance & History */}
            <div className="space-y-6">
              
              {/* Feature Importance */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <GitBranch className="w-5 h-5 text-emerald-500" />
                  Top Features
                </h3>
                <div className="space-y-3">
                  {bestModel?.feature_importance.slice(0, 8).map(([name, score]: any, idx: number) => {
                    const maxScore = bestModel.feature_importance[0][1];
                    const percent = Math.max((score / maxScore) * 100, 2);
                    return (
                      <div key={name}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="font-medium truncate pr-2" title={name}>{name.replace(/_/g, ' ')}</span>
                          <span className="text-[rgb(var(--text-secondary))]">{score.toFixed(3)}</span>
                        </div>
                        <div className="h-2 w-full bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  <div className="pt-2 text-xs text-center text-[rgb(var(--text-secondary))]">
                    Showing top 8 of {evaluation.dataset_metadata.feature_count} features
                  </div>
                </div>
              </div>

              {/* Dataset Stats */}
              <div className="card">
                <h3 className="text-sm font-semibold text-[rgb(var(--text-secondary))] mb-3 uppercase tracking-wider">
                  Dataset Summary
                </h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg text-center">
                    <div className="text-2xl font-bold">{evaluation.dataset_metadata.total_samples.toLocaleString()}</div>
                    <div className="text-xs text-[rgb(var(--text-secondary))] mt-1">Total Samples</div>
                  </div>
                  <div className="p-3 bg-[rgb(var(--bg-secondary))] rounded-lg text-center">
                    <div className="text-2xl font-bold">{evaluation.dataset_metadata.feature_count}</div>
                    <div className="text-xs text-[rgb(var(--text-secondary))] mt-1">Features Extracted</div>
                  </div>
                </div>
              </div>

              {/* Experiment History */}
              <div className="card">
                <h3 className="text-sm font-semibold text-[rgb(var(--text-secondary))] mb-3 uppercase tracking-wider">
                  Recent Experiments
                </h3>
                <div className="space-y-4">
                  {experiments?.map((exp: any) => (
                    <div key={exp.id} className="flex gap-3 relative">
                      <div className="flex flex-col items-center">
                        <div className={`w-2.5 h-2.5 rounded-full z-10 ${
                          exp.status === 'COMPLETED' ? 'bg-emerald-500' : 
                          exp.status === 'FAILED' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'
                        }`} />
                        <div className="w-0.5 h-full bg-[rgb(var(--border-color))] -mt-1" />
                      </div>
                      <div className="pb-4 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{exp.best_algorithm || 'Running...'}</span>
                          <span className="text-xs text-[rgb(var(--text-secondary))]">{formatDate(exp.created_at)}</span>
                        </div>
                        {exp.status === 'COMPLETED' && (
                          <div className="flex items-center gap-3 mt-1 text-xs">
                            <span className="text-brand-500 font-medium">F1: {(exp.best_f1 * 100).toFixed(1)}%</span>
                            <span className="text-[rgb(var(--text-secondary))]">{exp.total_training_time_seconds?.toFixed(1)}s</span>
                          </div>
                        )}
                        {exp.status === 'FAILED' && (
                          <div className="text-xs text-red-500 mt-1 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> Failed
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {experiments?.length === 0 && (
                    <div className="text-sm text-center text-[rgb(var(--text-secondary))]">
                      No experiments found.
                    </div>
                  )}
                </div>
              </div>

            </div>
          </div>
        </>
      ) : (
        <div className="card py-16 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-[rgb(var(--bg-secondary))] rounded-full flex items-center justify-center mb-4">
            <Brain className="w-8 h-8 text-[rgb(var(--text-secondary))]" />
          </div>
          <h2 className="text-xl font-bold mb-2">No ML Models Trained</h2>
          <p className="text-[rgb(var(--text-secondary))] max-w-md mb-6">
            The Machine Learning pipeline requires an initial training run.
            Generate the dataset and train the baseline models to view analytics.
          </p>
          <button
            onClick={handleTrain}
            disabled={isTraining}
            className="btn-primary"
          >
            {isTraining ? "Training in progress..." : "Start Initial Training"}
          </button>
        </div>
      )}
    </div>
  );
}
