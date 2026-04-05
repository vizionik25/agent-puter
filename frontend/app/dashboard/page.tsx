"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, loginWithGitHub, type GitHubUser } from "@/lib/auth";
import { myProjects, pushToGitHub, type ProjectSummary } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  intake: "Intake",
  planning: "Planning",
  execution: "Executing",
  qa: "QA Review",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const STATUS_COLOR: Record<string, string> = {
  intake: "#64748b",
  planning: "#a855f7",
  execution: "#3b82f6",
  qa: "#f59e0b",
  delivered: "#22c55e",
  cancelled: "#ef4444",
};

/**
 * Authenticated user dashboard that lists in-progress and delivered projects,
 * showing status badges, task progress bars, and actions for viewing, demoing, or pushing to GitHub.
 *
 * @returns {JSX.Element} The dashboard view, a sign-in prompt if unauthenticated, or a loading indicator.
 */
export default function DashboardPage() {
  const [user, setUser] = useState<GitHubUser | null | undefined>(undefined);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [pushing, setPushing] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const me = await getMe();
      setUser(me);
      if (me) {
        try {
          const list = await myProjects();
          setProjects(list);
        } catch {
          // empty — not authenticated or no projects yet
        }
      }
      setLoading(false);
    }
    load();
  }, []);

  async function handlePushGitHub(projectId: string) {
    setPushing(projectId);
    try {
      const result = await pushToGitHub(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === projectId ? { ...p, github_repo_url: result.repo_url } : p
        )
      );
    } catch (err) {
      alert(`Push failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPushing(null);
    }
  }

  if (loading) {
    return (
      <div className="container" style={{ paddingTop: "4rem", textAlign: "center" }}>
        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>Loading…</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container" style={{ paddingTop: "6rem", textAlign: "center" }}>
        <h2 style={{ marginBottom: "1rem" }}>Sign in to view your dashboard</h2>
        <p style={{ color: "var(--muted)", marginBottom: "2rem" }}>
          A GitHub account is required. One click — no forms, no passwords.
        </p>
        <button className="btn btn-primary" onClick={loginWithGitHub} style={{ padding: "0.75rem 2rem", fontSize: "1rem" }}>
          <GitHubIcon /> Sign in with GitHub
        </button>
      </div>
    );
  }

  const active = projects.filter((p) => !["delivered", "cancelled"].includes(p.status));
  const delivered = projects.filter((p) => p.status === "delivered");

  return (
    <div className="container" style={{ paddingTop: "3rem", paddingBottom: "4rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2.5rem", flexWrap: "wrap", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {user.avatar_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt={user.login} width={48} height={48} style={{ borderRadius: "50%" }} />
          )}
          <div>
            <h1 style={{ marginBottom: "0.2rem" }}>{user.name || user.login}</h1>
            <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              @{user.login} &middot; {user.tier.charAt(0).toUpperCase() + user.tier.slice(1)} plan &middot; {user.credits} credits
            </div>
          </div>
        </div>
        <Link href="/consult" className="btn btn-primary" style={{ padding: "0.65rem 1.5rem" }}>
          + New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🚀</div>
          <h3 style={{ marginBottom: "0.5rem" }}>No projects yet</h3>
          <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
            Start a free consultation to describe your project — the AI swarm will handle the rest.
          </p>
          <Link href="/consult" className="btn btn-primary">
            Start free consultation →
          </Link>
        </div>
      ) : (
        <>
          {active.length > 0 && (
            <section style={{ marginBottom: "3rem" }}>
              <h2 style={{ marginBottom: "1.25rem", fontSize: "1.1rem" }}>In progress</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
                {active.map((p) => <ProjectCard key={p.project_id} project={p} onPush={handlePushGitHub} pushing={pushing === p.project_id} />)}
              </div>
            </section>
          )}
          {delivered.length > 0 && (
            <section>
              <h2 style={{ marginBottom: "1.25rem", fontSize: "1.1rem" }}>Delivered</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
                {delivered.map((p) => <ProjectCard key={p.project_id} project={p} onPush={handlePushGitHub} pushing={pushing === p.project_id} />)}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ProjectCard({
  project: p,
  onPush,
  pushing,
}: {
  project: ProjectSummary;
  onPush: (id: string) => void;
  pushing: boolean;
}) {
  const color = STATUS_COLOR[p.status] ?? "#64748b";
  const label = STATUS_LABEL[p.status] ?? p.status;
  const pct = p.progress.total > 0 ? Math.round((p.progress.done / p.progress.total) * 100) : 0;

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {/* Status badge */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <h3 style={{ fontSize: "0.95rem", marginBottom: 0, flex: 1, marginRight: "0.5rem" }}>{p.name}</h3>
        <span style={{
          fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.04em",
          background: `${color}22`, color, borderRadius: "4px", padding: "0.2rem 0.5rem",
          whiteSpace: "nowrap",
        }}>
          {label}
        </span>
      </div>

      {/* Progress bar */}
      {p.progress.total > 0 && (
        <div>
          <div style={{ height: "4px", background: "var(--border)", borderRadius: "99px", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${pct}%`, background: color, transition: "width 0.4s" }} />
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
            {p.progress.done}/{p.progress.total} tasks
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "auto" }}>
        <Link href={`/status/${p.project_id}`} className="btn btn-outline" style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}>
          View
        </Link>
        {p.demo_available && (
          <Link href={`/demo/${p.project_id}`} className="btn btn-outline" style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}>
            Demo
          </Link>
        )}
        {p.github_repo_url ? (
          <a href={p.github_repo_url} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}>
            GitHub
          </a>
        ) : p.status === "delivered" ? (
          <button
            onClick={() => onPush(p.project_id)}
            disabled={pushing}
            className="btn btn-primary"
            style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
          >
            {pushing ? "Pushing…" : "Push to GitHub"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: "0.4rem" }}>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}
