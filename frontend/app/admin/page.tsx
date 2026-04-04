"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999";

interface ProjectSummary {
  project_id: string;
  name: string;
  client_id: string;
  owner_id: string;
  status: string;
  deposit_paid: boolean;
  final_paid: boolean;
  total_price_usd: number;
  llm_cost_usd: number;
  llm_requests: number;
  tokens_used: number;
  task_count: number;
  tasks_done: number;
  demo_url: string | null;
  deployment_status: string | null;
  created_at: string;
  updated_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  intake: "bg-slate-700 text-slate-200",
  planning: "bg-amber-900 text-amber-200",
  execution: "bg-violet-900 text-violet-200",
  qa: "bg-blue-900 text-blue-200",
  delivered: "bg-green-900 text-green-200",
  cancelled: "bg-red-900 text-red-200",
};

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ revenue: 0, cost: 0, projects: 0, delivered: 0 });

  async function load(key: string) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/admin/projects`, {
        headers: { "X-Admin-Key": key },
      });
      if (res.status === 401 || res.status === 503) {
        setError("Invalid admin key or admin not configured.");
        setLoading(false);
        return;
      }
      const data = await res.json();
      setProjects(data.projects ?? []);
      setAuthed(true);

      const revenue = data.projects.reduce(
        (sum: number, p: ProjectSummary) =>
          sum + (p.final_paid ? p.total_price_usd : p.deposit_paid ? p.total_price_usd * 0.2 : 0),
        0
      );
      const cost = data.projects.reduce((sum: number, p: ProjectSummary) => sum + p.llm_cost_usd, 0);
      const delivered = data.projects.filter((p: ProjectSummary) => p.status === "delivered").length;
      setStats({ revenue, cost, projects: data.total, delivered });
    } catch {
      setError("Failed to connect to backend.");
    }
    setLoading(false);
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="glass-card p-8 w-full max-w-sm space-y-4">
          <h1 className="text-2xl font-bold text-white">Admin Login</h1>
          <p className="text-slate-400 text-sm">Enter your ADMIN_API_KEY to continue.</p>
          <input
            type="password"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
            placeholder="Admin API Key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(adminKey)}
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            className="w-full btn-primary"
            onClick={() => load(adminKey)}
            disabled={loading || !adminKey}
          >
            {loading ? "Checking…" : "Sign In"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <button
            className="text-slate-400 hover:text-white text-sm"
            onClick={() => { setAuthed(false); setProjects([]); }}
          >
            Sign Out
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Projects", value: stats.projects },
            { label: "Delivered", value: stats.delivered },
            { label: "Revenue Collected", value: `$${stats.revenue.toFixed(2)}` },
            { label: "LLM Cost", value: `$${stats.cost.toFixed(4)}` },
          ].map((s) => (
            <div key={s.label} className="glass-card p-4 text-center">
              <div className="text-2xl font-bold text-violet-400">{s.value}</div>
              <div className="text-slate-400 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Projects table */}
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold">All Projects</h2>
            <button
              className="text-sm text-violet-400 hover:text-violet-300"
              onClick={() => load(adminKey)}
            >
              Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  {["Client", "Project", "Status", "Deposit", "Final", "Tasks", "LLM Cost", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {projects.map((p) => (
                  <tr key={p.project_id} className="hover:bg-slate-800/50">
                    <td className="px-4 py-3 text-slate-300">{p.client_id}</td>
                    <td className="px-4 py-3 font-medium">{p.name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[p.status] ?? ""}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {p.deposit_paid ? (
                        <span className="text-green-400">✓</span>
                      ) : (
                        <span className="text-slate-500">–</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {p.final_paid ? (
                        <span className="text-green-400">✓</span>
                      ) : (
                        <span className="text-slate-500">–</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.tasks_done}/{p.task_count}
                    </td>
                    <td className="px-4 py-3 text-slate-300">${p.llm_cost_usd.toFixed(4)}</td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/projects/${p.project_id}?key=${encodeURIComponent(adminKey)}`}
                        className="text-violet-400 hover:text-violet-300 text-xs"
                      >
                        Detail →
                      </Link>
                    </td>
                  </tr>
                ))}
                {projects.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                      No projects yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
