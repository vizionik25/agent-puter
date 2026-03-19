/**
 * app/demo/[id]/page.tsx — Live project demo viewer.
 *
 * Access control:
 *   - Checks GET /api/payments/{id}/status first.
 *   - If deposit_paid is false → shows locked state with link to /pay/{id}/deposit.
 *   - If deposit_paid is true  → fetches GET /api/projects/{id}/demo.
 *
 * Rendering modes (determined by the demo_url value):
 *   - URL (starts with "http") → renders an <iframe> sandbox + "Open ↗" link.
 *   - Plain text / notes       → renders a <pre> block (useful for text-only demos).
 *
 * The toolbar always shows a "Pay Balance & Receive →" CTA linking to /pay/{id}/final.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { demoGet, paymentStatus } from "@/lib/api";
import Link from "next/link";

export default function DemoPage() {
  const { id } = useParams<{ id: string }>();
  const [demoUrl, setDemoUrl] = useState<string | null>(null);
  const [depositPaid, setDepositPaid] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    paymentStatus(id).then((ps) => {
      setDepositPaid(ps.deposit_paid);
      if (ps.deposit_paid) {
        return demoGet(id).then((d) => setDemoUrl(d.demo_url));
      }
    }).catch((e: Error) => setError(e.message));
  }, [id]);

  if (depositPaid === false) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="card" style={{ maxWidth: 480, margin: "0 auto", padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔒</div>
          <h2 style={{ marginBottom: ".75rem", color: "#e2e8f0" }}>Demo locked</h2>
          <p style={{ marginBottom: "1.5rem" }}>A 20% deposit unlocks the live demo preview.</p>
          <Link href={`/pay/${id}/deposit`} className="btn btn-primary">Pay Deposit to Unlock →</Link>
        </div>
      </div>
    );
  }

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
        <p style={{ marginTop: "1rem" }}>
          {depositPaid === null ? "Checking access…" : "Demo is being prepared — check back shortly."}
        </p>
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
        <Link href={`/pay/${id}/final`} className="btn btn-primary" style={{ padding: ".45rem 1rem", fontSize: ".85rem" }}>
          Pay Balance & Receive →
        </Link>
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
