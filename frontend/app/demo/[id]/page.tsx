/**
 * app/demo/[id]/page.tsx — Live project demo viewer.
 *
 * Fetches the demo URL via GET /api/projects/{id}/demo.
 * Access is controlled by the backend (requires the project to be executed).
 *
 * Rendering modes (determined by the demo_url value):
 *   - URL (starts with "http") → renders an <iframe> sandbox + "Open ↗" link.
 *   - Plain text / notes       → renders a <pre> block.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { demoGet } from "@/lib/api";

/**
 * Live demo viewer page that fetches the project's demo URL and renders it either as a
 * sandboxed iframe (for HTTP URLs) or as a plain-text notes block.
 *
 * @returns {JSX.Element} The demo toolbar and iframe or text block, or an error/loading state.
 */
export default function DemoPage() {
  const { id } = useParams<{ id: string }>();
  const [demoUrl, setDemoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    demoGet(id)
      .then((d) => setDemoUrl(d.demo_url))
      .catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
      </div>
    );
  }

  if (!demoUrl) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="typing" style={{ justifyContent: "center" }}><span /><span /><span /></div>
        <p style={{ marginTop: "1rem" }}>Demo is being prepared — check back shortly.</p>
      </div>
    );
  }

  const isUrl = demoUrl.startsWith("http");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 65px)" }}>
      {/* Toolbar */}
      <div
        style={{
          padding: ".75rem 1.5rem",
          background: "var(--bg2)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          flexShrink: 0,
        }}
      >
        <span className="badge badge-green">🎉 Demo</span>
        <span style={{ fontSize: ".85rem", color: "var(--muted)", flex: 1 }}>{demoUrl}</span>
        {isUrl && (
          <a href={demoUrl} target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{ padding: ".45rem 1rem", fontSize: ".85rem" }}>
            Open ↗
          </a>
        )}
      </div>

      {/* Demo viewer */}
      {isUrl ? (
        <iframe
          src={demoUrl}
          style={{ flex: 1, border: "none", background: "#fff" }}
          title="Project Demo"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      ) : (
        <div className="container" style={{ padding: "3rem 1.5rem", maxWidth: 760, margin: "0 auto" }}>
          <div className="card" style={{ padding: "2rem" }}>
            <h3 style={{ marginBottom: "1rem", color: "#a78bfa" }}>Demo Notes</h3>
            <pre style={{ whiteSpace: "pre-wrap", color: "var(--text)", lineHeight: 1.7, fontSize: ".95rem" }}>{demoUrl}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
