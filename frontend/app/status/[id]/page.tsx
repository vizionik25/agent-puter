/**
 * app/status/[id]/page.tsx — Project status dashboard.
 *
 * Polls GET /api/projects/{id} every 8 seconds to display real-time
 * progress across the five project phases:
 *   intake → planning → execution → qa → delivered
 *
 * Shows:
 *  - Phase progress bar with step indicators
 *  - Per-task status list (pending / in_progress / review / done / failed)
 *  - View Demo CTA when project is delivered
 */
"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { projectGet, Project } from "@/lib/api";
import Link from "next/link";

const PHASE_ORDER = ["intake", "planning", "execution", "qa", "delivered"];
const STATUS_COLOR: Record<string, string> = {
  pending: "badge-amber",
  in_progress: "badge-violet",
  review: "badge-violet",
  done: "badge-green",
  failed: "badge-red",
};

export default function StatusPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    projectGet(id)
      .then(setProject)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [load]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="typing" style={{ justifyContent: "center" }}><span /><span /><span /></div>
        <p style={{ marginTop: "1rem" }}>Loading project…</p>
      </div>
    );
  }

  const phaseIdx = PHASE_ORDER.indexOf(project.status);
  const phasePct = Math.round(((phaseIdx + 1) / PHASE_ORDER.length) * 100);
  const doneTasks = project.tasks.filter((t) => t.status === "done").length;
  const totalTasks = project.tasks.length;
  const taskPct = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0;

  return (
    <div className="container" style={{ padding: "3rem 1.5rem", maxWidth: 760, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "2rem" }}>
        <div>
          <span className="badge badge-violet" style={{ marginBottom: ".5rem" }}>📊 Status</span>
          <h1 style={{ fontSize: "1.8rem" }}>{project.name}</h1>
          <p style={{ fontSize: ".9rem", marginTop: ".25rem" }}>{project.description}</p>
        </div>
        {project.status === "delivered" && (
          <Link href={`/demo/${id}`} className="btn btn-primary" style={{ padding: ".5rem 1rem", fontSize: ".85rem" }}>
            View Demo →
          </Link>
        )}
      </div>

      {/* Phase tracker */}
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: ".75rem" }}>
          <h3>Project Phase</h3>
          <span className="badge badge-violet" style={{ textTransform: "capitalize" }}>{project.status}</span>
        </div>
        <div className="progress-track" style={{ marginBottom: "1rem" }}>
          <div className="progress-fill" style={{ width: `${phasePct}%` }} />
        </div>
        <div style={{ display: "flex", gap: "0", overflowX: "auto" }}>
          {PHASE_ORDER.map((phase, i) => (
            <div key={phase} style={{ flex: 1, textAlign: "center" }}>
              <div
                style={{
                  width: 28, height: 28, borderRadius: "50%", margin: "0 auto .4rem",
                  background: i <= phaseIdx ? "var(--violet-g)" : "var(--surface-h)",
                  border: `2px solid ${i <= phaseIdx ? "rgba(109,40,217,.6)" : "var(--border)"}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: ".75rem", fontWeight: 700, color: i <= phaseIdx ? "#fff" : "var(--muted)",
                  transition: "all .3s",
                }}
              >
                {i < phaseIdx ? "✓" : i + 1}
              </div>
              <div style={{ fontSize: ".7rem", color: i <= phaseIdx ? "var(--text)" : "var(--muted)", textTransform: "capitalize" }}>
                {phase}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Task progress */}
      {totalTasks > 0 && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: ".75rem" }}>
            <h3>Tasks</h3>
            <span style={{ fontSize: ".9rem", color: "var(--muted)" }}>{doneTasks}/{totalTasks}</span>
          </div>
          <div className="progress-track" style={{ marginBottom: "1.25rem" }}>
            <div className="progress-fill" style={{ width: `${taskPct}%` }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: ".6rem" }}>
            {project.tasks.map((task) => (
              <div
                key={task.id}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: ".75rem 1rem", borderRadius: "var(--radius-sm)",
                  background: "var(--surface-h)", border: "1px solid var(--border)",
                }}
              >
                <div>
                  <div style={{ fontSize: ".9rem", fontWeight: 500, color: "var(--text)" }}>{task.title}</div>
                  {task.assigned_to && (
                    <div style={{ fontSize: ".75rem", color: "var(--muted)", marginTop: ".2rem" }}>
                      👤 {task.assigned_to}
                    </div>
                  )}
                </div>
                <span className={`badge ${STATUS_COLOR[task.status] ?? "badge-amber"}`} style={{ textTransform: "capitalize" }}>
                  {task.status.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p style={{ fontSize: ".75rem", color: "var(--muted)", marginTop: "1rem", textAlign: "center" }}>
        Auto-refreshes every 8 seconds
      </p>
    </div>
  );
}
