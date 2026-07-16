"use client";

import React, { useState, useEffect } from "react";
import { graphService } from "@/services/graph";
import { apiClient } from "@/services/api";
import {
  GitPullRequest, Filter, Info, Play, RefreshCw, ZoomIn, ZoomOut, Maximize2, ShieldAlert, BarChart3, ListFilter, Cpu, Layers, HelpCircle
} from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: any;
  x?: number;
  y?: number;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight: number;
  confidence: number;
}

interface Community {
  community_id: number;
  node_ids: string[];
}

export default function GraphDashboardPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const [metrics, setMetrics] = useState<any>(null);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [hubs, setHubs] = useState<any[]>([]);
  const [centralities, setCentralities] = useState<any[]>([]);

  const [traversalNodeId, setTraversalNodeId] = useState<string>("");
  const [traversalMethod, setTraversalMethod] = useState<"bfs" | "dfs">("bfs");
  const [traversalDepth, setTraversalDepth] = useState<number>(2);
  const [traversalExplanation, setTraversalExplanation] = useState<string[]>([]);
  const [highlightedNodes, setHighlightedNodes] = useState<string[]>([]);

  const [visibleTypes, setVisibleTypes] = useState<string[]>([
    "Document", "Paragraph", "PERSON", "ORGANIZATION", "ADDRESS", "PHONE", "EMAIL", "CONTRACT", "CLAUSE"
  ]);

  const width = 800;
  const height = 500;

  const loadDocuments = async () => {
    try {
      const res = await apiClient.getDocuments();
      setDocuments(res.documents || []);
      if (res.documents && res.documents.length > 0) {
        setSelectedDocId(res.documents[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadGraphData = async (docId: string) => {
    if (!docId) return;
    try {
      const res = await graphService.getDocumentSubgraph(docId);
      const rawNodes = res.nodes || [];
      const rawEdges = res.edges || [];

      const laidNodes = layoutNodes(rawNodes, rawEdges);
      setNodes(laidNodes);
      setEdges(rawEdges);
      setSelectedNode(null);
      setHighlightedNodes([]);
      setTraversalExplanation([]);

      if (res.document_version_id) {
        const stats = await graphService.getStatistics(res.document_version_id);
        setMetrics(stats.observability || null);
        setCommunities(stats.analytics?.communities || []);
        setHubs(stats.analytics?.hubs || []);
        setCentralities(stats.analytics?.betweenness_centrality || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadGraphData(selectedDocId);
    }
  }, [selectedDocId]);

  const layoutNodes = (nodesList: GraphNode[], edgesList: GraphEdge[]): GraphNode[] => {
    const total = nodesList.length;
    if (total === 0) return [];
    
    const laid = nodesList.map((n, idx) => {
      const angle = (idx / total) * 2 * Math.PI;
      const radius = 150 + Math.random() * 50;
      return {
        ...n,
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle)
      };
    });

    const iterations = 40;
    const k = Math.sqrt((width * height) / total) * 0.75;
    
    for (let iter = 0; iter < iterations; iter++) {
      for (let i = 0; i < total; i++) {
        const n1 = laid[i];
        n1.properties.dx = 0;
        n1.properties.dy = 0;
        for (let j = 0; j < total; j++) {
          if (i === j) continue;
          const n2 = laid[j];
          const dx = n1.x! - n2.x!;
          const dy = n1.y! - n2.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 200) {
            const force = (k * k) / dist;
            n1.properties.dx += (dx / dist) * force * 0.15;
            n1.properties.dy += (dy / dist) * force * 0.15;
          }
        }
      }

      edgesList.forEach((e) => {
        const sourceNode = laid.find((n) => n.id === e.source);
        const targetNode = laid.find((n) => n.id === e.target);
        if (sourceNode && targetNode) {
          const dx = targetNode.x! - sourceNode.x!;
          const dy = targetNode.y! - sourceNode.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist * dist) / k;
          sourceNode.properties.dx += (dx / dist) * force * 0.1;
          sourceNode.properties.dy += (dy / dist) * force * 0.1;
          targetNode.properties.dx -= (dx / dist) * force * 0.1;
          targetNode.properties.dy -= (dy / dist) * force * 0.1;
        }
      });

      laid.forEach((n) => {
        n.x = Math.max(40, Math.min(width - 40, n.x! + n.properties.dx));
        n.y = Math.max(40, Math.min(height - 40, n.y! + n.properties.dy));
      });
    }

    return laid;
  };

  const handleTraverse = async () => {
    if (!traversalNodeId) return;
    try {
      const res = await graphService.traverseGraph({
        start_node_id: traversalNodeId,
        method: traversalMethod,
        max_depth: traversalDepth
      });
      setTraversalExplanation(res.explainability || []);
      const visitedIds = (res.nodes || []).map((n: any) => n.id);
      setHighlightedNodes(visitedIds);
    } catch (err) {
      console.error(err);
    }
  };

  const toggleTypeFilter = (type: string) => {
    setVisibleTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const getNodeColor = (type: string) => {
    switch (type.toUpperCase()) {
      case "DOCUMENT":
        return "#ef4444";
      case "PARAGRAPH":
        return "#3b82f6";
      case "PERSON":
        return "#10b981";
      case "ORGANIZATION":
        return "#8b5cf6";
      case "ADDRESS":
        return "#f59e0b";
      case "CLAUSE":
        return "#ec4899";
      default:
        return "#64748b";
    }
  };

  const filteredNodes = nodes.filter((n) => visibleTypes.includes(n.type));
  const filteredNodeIds = filteredNodes.map((n) => n.id);
  const filteredEdges = edges.filter(
    (e) => filteredNodeIds.includes(e.source) && filteredNodeIds.includes(e.target)
  );

  return (
    <div className="text-slate-100 font-sans space-y-6 h-[85vh] flex flex-col">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/[0.06] pb-4 shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-brand-500" /> Enterprise Knowledge Graph Explorer
          </h1>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Visualize legal entities, document hierarchies, and structural dependencies.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Target document:</span>
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="bg-slate-900 border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
          <button
            onClick={() => loadGraphData(selectedDocId)}
            className="p-2.5 bg-slate-900 border border-white/[0.08] hover:bg-slate-800 rounded-xl text-slate-300 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        <div className="flex-1 bg-slate-900/40 border border-white/[0.05] rounded-2xl flex flex-col relative overflow-hidden backdrop-blur-xl min-h-[350px]">
          <div className="absolute top-4 left-4 z-10 bg-[#090B12]/80 border border-white/[0.08] rounded-xl p-3 text-[10px] space-y-1.5 backdrop-blur">
            <span className="font-bold text-slate-300 uppercase block mb-1">Color Key:</span>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {[
                { label: "Document", type: "Document" },
                { label: "Paragraph", type: "Paragraph" },
                { label: "Clause", type: "Clause" },
                { label: "Person", type: "PERSON" },
                { label: "Organization", type: "ORGANIZATION" },
                { label: "Address", type: "ADDRESS" }
              ].map((key) => (
                <div key={key.type} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block"
                    style={{ backgroundColor: getNodeColor(key.type) }}
                  />
                  <span>{key.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 relative cursor-grab active:cursor-grabbing">
            {nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 italic text-xs">
                No graph nodes generated for this version. Try selecting another document.
              </div>
            ) : (
              <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="select-none">
                {filteredEdges.map((edge) => {
                  const srcNode = nodes.find((n) => n.id === edge.source);
                  const tgtNode = nodes.find((n) => n.id === edge.target);
                  if (!srcNode || !tgtNode) return null;
                  
                  const isHighlighted =
                    highlightedNodes.includes(edge.source) && highlightedNodes.includes(edge.target);

                  return (
                    <g key={edge.id}>
                      <line
                        x1={srcNode.x}
                        y1={srcNode.y}
                        x2={tgtNode.x}
                        y2={tgtNode.y}
                        stroke={isHighlighted ? "#fbbf24" : "#ffffff"}
                        strokeOpacity={isHighlighted ? 0.8 : 0.15}
                        strokeWidth={isHighlighted ? 2.5 : 1}
                      />
                      <text
                        x={(srcNode.x! + tgtNode.x!) / 2}
                        y={(srcNode.y! + tgtNode.y!) / 2 - 4}
                        fill={isHighlighted ? "#fbbf24" : "#64748b"}
                        fillOpacity={isHighlighted ? 0.9 : 0.5}
                        fontSize="7px"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {edge.relation}
                      </text>
                    </g>
                  );
                })}

                {filteredNodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  const isHighlighted = highlightedNodes.includes(node.id);
                  const nodeSize = node.type === "Document" ? 14 : node.type === "Paragraph" ? 10 : 7;
                  
                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      onClick={() => {
                        setSelectedNode(node);
                        setTraversalNodeId(node.id);
                      }}
                      className="cursor-pointer group"
                    >
                      <circle
                        r={nodeSize + (isSelected ? 3 : 0)}
                        fill={getNodeColor(node.type)}
                        stroke={isHighlighted ? "#fbbf24" : isSelected ? "#ffffff" : "none"}
                        strokeWidth={isHighlighted || isSelected ? 2 : 0}
                        className="transition-all hover:scale-125"
                      />
                      <text
                        y={nodeSize + 11}
                        fill="#f1f5f9"
                        fontSize="8px"
                        fontWeight="600"
                        textAnchor="middle"
                        className="opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900"
                      >
                        {node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </div>

        <div className="w-full lg:w-96 flex flex-col gap-6 overflow-y-auto pr-1 shrink-0">
          <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-4 space-y-4">
            <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
              <Info className="w-4 h-4 text-brand-500" /> Node Inspector
            </h2>
            {selectedNode ? (
              <div className="space-y-3 text-[11px]">
                <div>
                  <span className="text-slate-500">Label:</span>
                  <p className="text-slate-200 font-bold text-xs mt-0.5">{selectedNode.label}</p>
                </div>
                <div>
                  <span className="text-slate-500">Node Type:</span>
                  <p className="text-brand-400 font-semibold mt-0.5">{selectedNode.type}</p>
                </div>
                {selectedNode.properties && (
                  <div className="space-y-2 pt-2 border-t border-white/[0.04]">
                    {selectedNode.properties.page_number && (
                      <div>
                        <span className="text-slate-500">Page number:</span>
                        <p className="text-slate-300 mt-0.5">{selectedNode.properties.page_number}</p>
                      </div>
                    )}
                    {selectedNode.properties.extraction_confidence && (
                      <div>
                        <span className="text-slate-500">Confidence Score:</span>
                        <p className="text-emerald-400 mt-0.5">
                          {Math.round(selectedNode.properties.extraction_confidence * 100)}%
                        </p>
                      </div>
                    )}
                    {selectedNode.properties.text && (
                      <div>
                        <span className="text-slate-500">Paragraph Content:</span>
                        <p className="text-slate-400 mt-1 max-h-[100px] overflow-y-auto leading-normal bg-slate-950/40 p-2 rounded border border-white/[0.03]">
                          {selectedNode.properties.text}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">Click a node on the canvas to inspect provenance properties.</p>
            )}
          </div>

          <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-4 space-y-4">
            <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
              <GitPullRequest className="w-4 h-4 text-brand-500" /> Graph Path Traversal
            </h2>
            <div className="space-y-3.5 text-xs">
              <div className="flex flex-col gap-1.5">
                <span className="text-slate-500">Select algorithm:</span>
                <div className="flex gap-2">
                  {["bfs", "dfs"].map((m) => (
                    <button
                      key={m}
                      onClick={() => setTraversalMethod(m as any)}
                      className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold uppercase transition ${
                        traversalMethod === m
                          ? "bg-brand-500 text-white"
                          : "bg-slate-900 border border-white/[0.06] text-slate-400 hover:bg-slate-800"
                      }`}
                    >
                      {m} Mode
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <span className="text-slate-500">Traversal depth (Max hops):</span>
                <input
                  type="range"
                  min="1"
                  max="4"
                  value={traversalDepth}
                  onChange={(e) => setTraversalDepth(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-brand-500"
                />
                <span className="text-[10px] text-right text-brand-400 font-bold">{traversalDepth} Hops</span>
              </div>

              <button
                onClick={handleTraverse}
                disabled={!traversalNodeId}
                className="w-full py-2 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/30 text-white font-bold rounded-xl flex items-center justify-center gap-1.5 transition text-xs"
              >
                <Play className="w-3.5 h-3.5" /> Execute Traversal
              </button>

              {traversalExplanation.length > 0 && (
                <div className="pt-3 border-t border-white/[0.04] space-y-2">
                  <span className="text-slate-500 text-[10px] uppercase font-bold block">Traversal paths log:</span>
                  <div className="space-y-1.5 max-h-[120px] overflow-y-auto pr-1">
                    {traversalExplanation.map((line, lIdx) => (
                      <div key={lIdx} className="text-[10px] text-amber-400 bg-amber-500/5 border border-amber-500/10 p-2 rounded-lg leading-normal">
                        🔍 {line}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {metrics && (
            <div className="bg-[#0c0f17]/40 border border-white/[0.05] rounded-2xl p-4 space-y-4">
              <h2 className="text-xs font-bold text-[#AEB6C4] uppercase tracking-wider flex items-center gap-1.5">
                <BarChart3 className="w-4 h-4 text-brand-500" /> Observability metrics
              </h2>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="bg-[#090B12]/60 border border-white/[0.03] p-3 rounded-xl">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500">Nodes Count</span>
                  <p className="text-slate-200 font-bold text-sm mt-1">{metrics.node_count}</p>
                </div>
                <div className="bg-[#090B12]/60 border border-white/[0.03] p-3 rounded-xl">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500">Edges Count</span>
                  <p className="text-slate-200 font-bold text-sm mt-1">{metrics.edge_count}</p>
                </div>
                <div className="bg-[#090B12]/60 border border-white/[0.03] p-3 rounded-xl">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500">Density</span>
                  <p className="text-slate-200 font-bold text-sm mt-1">{metrics.density}</p>
                </div>
                <div className="bg-[#090B12]/60 border border-white/[0.03] p-3 rounded-xl">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500">Average Degree</span>
                  <p className="text-slate-200 font-bold text-sm mt-1">{metrics.avg_degree}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
