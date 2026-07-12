"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldAlert, Activity, Key, ShieldCheck, Download, Play, 
  Trash2, RefreshCw, AlertTriangle, List, CheckCircle2 
} from "lucide-react";

interface SecurityStats {
  score: {
    authentication: number;
    rbac: number;
    api_security: number;
    document_security: number;
    audit: number;
    secrets: number;
    total: number;
  };
  active_sessions: number;
  total_alerts: number;
  failed_logins: number;
  audit_logs_count: number;
}

interface ActiveSession {
  id: string;
  user_email: string;
  ip_address: string;
  user_agent: string;
  last_active_at: string;
}

interface AuditLog {
  id: string;
  user_email: string;
  action: string;
  resource: string;
  result: string;
  created_at: string;
}

interface SecurityAlert {
  id: string;
  event_type: string;
  severity: string;
  description: string;
  created_at: string;
}

export default function SecurityPage() {
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [runningTests, setRunningTests] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchSecurityData = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const headers = { Authorization: `Bearer ${token}` };

      // Stats
      const statsRes = await fetch("http://localhost:8000/api/v1/security/stats", { headers });
      const statsData = await statsRes.json();
      setStats(statsData);

      // Sessions
      const sessionsRes = await fetch("http://localhost:8000/api/v1/security/sessions", { headers });
      const sessionsData = await sessionsRes.json();
      setSessions(Array.isArray(sessionsData) ? sessionsData : []);

      // Audit Logs
      const auditRes = await fetch("http://localhost:8000/api/v1/security/audit", { headers });
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        setAuditLogs(Array.isArray(auditData) ? auditData : []);
      }

      // Alerts
      const alertsRes = await fetch("http://localhost:8000/api/v1/security/alerts", { headers });
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
      }

      setLoading(false);
    } catch (err) {
      console.error("Error loading security dashboard data:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityData();
  }, []);

  const triggerSecurityTests = async () => {
    setRunningTests(true);
    setMessage(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("http://localhost:8000/api/v1/security/test", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Security validation tests completed successfully! PDF compiled." });
        await fetchSecurityData();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Only Administrators can run security tests." });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Connection error triggering tests." });
    }
    setRunningTests(false);
  };

  const downloadPDFReport = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("http://localhost:8000/api/v1/security/report/download", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "RedactAI_Security_Report.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        alert("Failed to download PDF report.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const revokeSession = async (sessionId: string) => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("http://localhost:8000/api/v1/security/sessions/revoke", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({ session_id: sessionId })
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Session revoked successfully." });
        await fetchSecurityData();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Could not revoke session." });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Error connecting to session endpoint." });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const score = stats?.score?.total || 0;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[rgb(var(--text-primary))]">
            Enterprise Security Hardening Dashboard
          </h2>
          <p className="text-sm text-[rgb(var(--text-secondary))] mt-1">
            Real-time security telemetry, active session controls, compliance scoring, and OWASP testing.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={triggerSecurityTests}
            disabled={runningTests}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Play className={`w-4 h-4 ${runningTests ? "animate-pulse" : ""}`} />
            {runningTests ? "Testing..." : "Execute Vulnerability Tests"}
          </button>
          <button
            onClick={downloadPDFReport}
            className="btn btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download PDF Report
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-xl flex items-center gap-3 ${
          message.type === "success" 
            ? "bg-green-500/10 text-green-500 border border-green-500/25" 
            : "bg-red-500/10 text-red-500 border border-red-500/25"
        }`}>
          <ShieldCheck className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{message.text}</span>
        </div>
      )}

      {/* Main Score and Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Posture Score Gauge */}
        <div className="glass-card p-6 flex flex-col items-center justify-center text-center">
          <h3 className="text-sm font-semibold text-[rgb(var(--text-secondary))] uppercase tracking-wider mb-4">
            Security Posture Score
          </h3>
          <div className="relative flex items-center justify-center w-40 h-40">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="rgba(var(--border-color), 0.2)"
                strokeWidth="10"
                fill="transparent"
              />
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="rgb(var(--brand-primary))"
                strokeWidth="10"
                fill="transparent"
                strokeDasharray="440"
                strokeDashoffset={440 - (440 * score) / 100}
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-4xl font-extrabold tracking-tight text-[rgb(var(--text-primary))]">
                {score}
              </span>
              <span className="text-xs text-[rgb(var(--text-secondary))] mt-0.5">
                Rating: SECURE
              </span>
            </div>
          </div>
          <p className="text-xs text-[rgb(var(--text-secondary))] mt-6 max-w-[200px]">
            Based on active session constraints, MFA, RBAC guards, rate limit configurations, and encryption keys.
          </p>
        </div>

        {/* Breakdown Card */}
        <div className="glass-card p-6 col-span-2">
          <h3 className="text-lg font-bold text-[rgb(var(--text-primary))] mb-4">
            Security Controls Breakdown
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm font-medium mb-1">
                <span>Authentication & Lockouts</span>
                <span>{stats?.score?.authentication || 0} / 20</span>
              </div>
              <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.authentication || 0) / 20) * 100}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm font-medium mb-1">
                <span>Role-Based Access Control (RBAC)</span>
                <span>{stats?.score?.rbac || 0} / 20</span>
              </div>
              <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.rbac || 0) / 20) * 100}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm font-medium mb-1">
                <span>API Security (Headers & Limits)</span>
                <span>{stats?.score?.api_security || 0} / 20</span>
              </div>
              <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.api_security || 0) / 20) * 100}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm font-medium mb-1">
                <span>Document Integrity Verification (SHA-256)</span>
                <span>{stats?.score?.document_security || 0} / 20</span>
              </div>
              <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.document_security || 0) / 20) * 100}%` }} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-1">
              <div>
                <div className="flex justify-between text-sm font-medium mb-1">
                  <span>Structured Audit Logs</span>
                  <span>{stats?.score?.audit || 0} / 10</span>
                </div>
                <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                  <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.audit || 0) / 10) * 100}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm font-medium mb-1">
                  <span>Secrets Startup Checks</span>
                  <span>{stats?.score?.secrets || 0} / 10</span>
                </div>
                <div className="w-full h-2 bg-[rgb(var(--bg-secondary))] rounded-full overflow-hidden">
                  <div className="h-full bg-brand-500 rounded-full" style={{ width: `${((stats?.score?.secrets || 0) / 10) * 100}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Telemetry Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-3 bg-brand-500/10 rounded-xl text-brand-500">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{stats?.active_sessions}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))]">Active Sessions</p>
          </div>
        </div>

        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-3 bg-red-500/10 rounded-xl text-red-500">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight text-red-500">{stats?.total_alerts}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))]">Security Alerts</p>
          </div>
        </div>

        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-3 bg-amber-500/10 rounded-xl text-amber-500">
            <Key className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{stats?.failed_logins}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))]">Failed Logins</p>
          </div>
        </div>

        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-3 bg-green-500/10 rounded-xl text-green-500">
            <List className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{stats?.audit_logs_count}</p>
            <p className="text-xs text-[rgb(var(--text-secondary))]">Audit Entries</p>
          </div>
        </div>
      </div>

      {/* Active Sessions Panel */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-bold text-[rgb(var(--text-primary))] mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-brand-500" />
          Active Logged Sessions Control
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[rgb(var(--border-color))]/50 text-[rgb(var(--text-secondary))]">
                <th className="py-3 px-4">User Session</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4">User Agent</th>
                <th className="py-3 px-4">Revocation</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id} className="border-b border-[rgb(var(--border-color))]/30 hover:bg-[rgb(var(--bg-secondary))]/30">
                  <td className="py-3.5 px-4 font-medium text-[rgb(var(--text-primary))]">{s.user_email}</td>
                  <td className="py-3.5 px-4 text-[rgb(var(--text-secondary))]">{s.ip_address}</td>
                  <td className="py-3.5 px-4 text-[rgb(var(--text-secondary))] truncate max-w-[200px]" title={s.user_agent}>
                    {s.user_agent}
                  </td>
                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => revokeSession(s.id)}
                      className="text-red-500 hover:text-red-600 font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Terminate
                    </button>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-[rgb(var(--text-secondary))]">
                    No active sessions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alerts and Audits Feed Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Security Alerts */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-bold text-[rgb(var(--text-primary))] mb-4 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            Security Alerts log
          </h3>
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
            {alerts.map((a) => (
              <div key={a.id} className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-red-400">{a.event_type}</span>
                    <span className="text-[10px] text-[rgb(var(--text-secondary))]">
                      {new Date(a.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-xs text-[rgb(var(--text-secondary))] mt-1">{a.description}</p>
                </div>
              </div>
            ))}
            {alerts.length === 0 && (
              <p className="text-sm text-[rgb(var(--text-secondary))] text-center py-12">
                No active security warnings. System secure.
              </p>
            )}
          </div>
        </div>

        {/* Audit Log Trail */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-bold text-[rgb(var(--text-primary))] mb-4 flex items-center gap-2">
            <List className="w-5 h-5 text-brand-500" />
            Recent Activity Audit Trail
          </h3>
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-3 bg-[rgb(var(--bg-secondary))]/40 border border-[rgb(var(--border-color))]/30 rounded-xl flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[rgb(var(--text-primary))]">{log.action}</span>
                    <span className="text-[10px] bg-green-500/10 text-green-500 px-1.5 py-0.5 rounded font-medium">
                      {log.result}
                    </span>
                  </div>
                  <p className="text-[10px] text-[rgb(var(--text-secondary))] mt-1">{log.resource} | {log.user_email}</p>
                </div>
                <span className="text-[10px] text-[rgb(var(--text-secondary))]">
                  {new Date(log.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
            {auditLogs.length === 0 && (
              <p className="text-sm text-[rgb(var(--text-secondary))] text-center py-12">
                No recent audit activities logged.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
