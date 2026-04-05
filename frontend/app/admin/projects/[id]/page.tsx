"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999";

interface Task {
  id: string;
  title: string;
  description: string;
  assigned_to: string | null;
  status: string;
  retry_count: number;
  tokens_used: number;
  cost_usd: number;
  output: string | null;
  qa_feedback: string | null;
}

interface ProjectDetail {
  project_id: string;
  name: string;
  description: string;
  client_id: string;
  owner_id: string;
  status: string;
  deposit_paid: boolean;
  final_paid: boolean;
  total_price_usd: number;
  llm_cost_usd: number;
  llm_requests: number;
  tokens_used: number;
  demo_url: string | null;
  deployment_status: string | null;
  tasks: Task[];
  proposal: Record<string, unknown> | null;
}

interface LogEntry {
  timestamp: string;
  level: string;
  source: string;
  message: string;
  project_id: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-slate-700 text-slate-200",
  in_progress: "bg-violet-900 text-violet-200",
  review: "bg-amber-900 text-amber-200",
  done: "bg-green-900 text-green-200",
  failed: "bg-red-900 text-red-200",
};

/**
 * Admin detail page for a single project showing metrics, an editable demo URL setter,
 * a collapsible per-task output and QA feedback list, and a filtered recent log stream.
 *
 * @returns {JSX.Element} The full project detail view, or a loading/error state.
 */
export default function AdminProjectPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const adminKey = searchParams.get("key") ?? "";

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [demoUrl, setDemoUrl] = useState("");
  const [demoMsg, setDemoMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [pRes, lRes] = await Promise.all([
        fetch(`${API}/api/admin/projects/${params.id}`, {
          headers: { "X-Admin-Key": adminKey },
        }),
        fetch(`${API}/api/admin/logs?limit=50`, {
          headers: { "X-Admin-Key": adminKey },
        }),
      ]);
      if (!pRes.ok) {
        setError("Project not found or unauthorised.");
        setLoading(false);
        return;
      }
      const pData = await pRes.json();
      setProject(pData);
      setDemoUrl(pData.demo_url ?? "");

      if (lRes.ok) {
        const lData = await lRes.json();
        const filtered = (lData.logs as LogEntry[]).filter(
          (l) => l.project_id === params.id || l.project_id === ""
        );
        setLogs(filtered);
      }
    } catch {
      setError("Failed to load project.");
    }
    setLoading(false);
  }

  async function setDemo() {
    setDemoMsg("");
    const res = await fetch(`${API}/api/admin/projects/${params.id}/demo-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
      body: JSON.stringify({ demo_url: demoUrl }),
    });
    if (res.ok) {
      setDemoMsg("Demo URL updated.");
      load();
    } else {
      setDemoMsg("Failed to update demo URL.");
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-violet-400 animate-pulse">Loading…</div>
    </div>
  );

  if (error || !project) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-red-400">{error || "Project not found."}</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back */}
        <Link href="/admin" className="text-violet-400 hover:text-violet-300 text-sm">
          ← Admin Dashboard
        </Link>

        {/* Header */}
        <div className="glass-card p-6 space-y-2">
          <div className="flex items-start justify-between flex-wrap gap-2">
            <div>
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <p className="text-slate-400 text-sm mt-1">{project.client_id} · tenant: {project.owner_id}</p>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              project.status === "delivered" ? "bg-green-900 text-green-200" : "bg-violet-900 text-violet-200"
            }`}>
              {project.status}
            </span>
          </div>
          <p className="text-slate-300 text-sm">{project.description}</p>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Price", value: `$${project.total_price_usd.toFixed(2)}` },
            { label: "LLM Cost", value: `$${project.llm_cost_usd.toFixed(4)}` },
            { label: "LLM Requests", value: project.llm_requests },
            { label: "Tokens Used", value: project.tokens_used.toLocaleString() },
          ].map((m) => (
            <div key={m.label} className="glass-card p-4 text-center">
              <div className="text-xl font-bold text-violet-400">{m.value}</div>
              <div className="text-slate-400 text-xs mt-1">{m.label}</div>
            </div>
          ))}
        </div>

        {/* Demo URL setter */}
        <div className="glass-card p-6 space-y-3">
          <h2 className="font-semibold">Demo URL</h2>
          {project.demo_url && (
            <a href={project.demo_url} target="_blank" rel="noreferrer"
              className="text-violet-400 hover:underline text-sm break-all">
              {project.demo_url}
            </a>
          )}
          <div className="flex gap-2">
            <input
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500"
              placeholder="https://... or sandbox URL"
              value={demoUrl}
              onChange={(e) => setDemoUrl(e.target.value)}
            />
            <button className="btn-primary text-sm px-4" onClick={setDemo}>
              Set
            </button>
          </div>
          {demoMsg && <p className="text-green-400 text-sm">{demoMsg}</p>}
          {project.deployment_status && (
            <p className="text-slate-400 text-xs">Deployment: {project.deployment_status}</p>
          )}
        </div>

        {/* Tasks */}
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="font-semibold">Tasks ({project.tasks.length})</h2>
          </div>
          <div className="divide-y divide-slate-800">
            {project.tasks.map((task) => (
              <div key={task.id} className="p-4">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[task.status] ?? ""}`}>
                      {task.status}
                    </span>
                    <span className="font-medium text-sm">{task.title}</span>
                    {task.retry_count > 0 && (
                      <span className="text-amber-400 text-xs">{task.retry_count} retries</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span>{task.tokens_used} tok · ${task.cost_usd.toFixed(4)}</span>
                    <span>{expandedTask === task.id ? "▲" : "▼"}</span>
                  </div>
                </div>

                {expandedTask === task.id && (
                  <div className="mt-3 space-y-2 text-sm">
                    <p className="text-slate-400">{task.description}</p>
                    {task.output && (
                      <div>
                        <p className="text-slate-500 text-xs mb-1">Output:</p>
                        <pre className="bg-slate-900 rounded p-3 text-slate-300 text-xs overflow-x-auto whitespace-pre-wrap max-h-64">
                          {task.output}
                        </pre>
                      </div>
                    )}
                    {task.qa_feedback && (
                      <div>
                        <p className="text-slate-500 text-xs mb-1">QA Feedback:</p>
                        <pre className="bg-slate-900 rounded p-3 text-amber-200 text-xs overflow-x-auto whitespace-pre-wrap max-h-32">
                          {task.qa_feedback}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {project.tasks.length === 0 && (
              <div className="p-6 text-center text-slate-500 text-sm">No tasks yet.</div>
            )}
          </div>
        </div>

        {/* Logs */}
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold">Recent Logs</h2>
            <button className="text-xs text-violet-400 hover:text-violet-300" onClick={load}>
              Refresh
            </button>
          </div>
          <div className="divide-y divide-slate-800 max-h-80 overflow-y-auto">
            {logs.map((log, i) => (
              <div key={i} className="px-4 py-2 flex gap-3 text-xs font-mono">
                <span className="text-slate-500 shrink-0">{log.timestamp.split("T")[1].split(".")[0]}</span>
                <span className={`shrink-0 ${log.level === "warn" ? "text-amber-400" : "text-violet-400"}`}>
                  [{log.source}]
                </span>
                <span className="text-slate-300">{log.message}</span>
              </div>
            ))}
            {logs.length === 0 && (
              <div className="p-4 text-center text-slate-500 text-xs">No logs for this project.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
