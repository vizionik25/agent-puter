/**
 * app/proposal/[id]/page.tsx — Project proposal viewer.
 *
 * Fetches the proposal via GET /api/projects/{id}/proposal and renders:
 *  - Problem statement & solution overview
 *  - Implementation plan
 *  - Deliverables list
 *  - Credit cost & balance (replaces the old Stripe deposit CTA)
 *
 * Returns a 404-style error card if the proposal is not yet ready.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { proposalGet, Proposal } from "@/lib/api";
import { getState, canExecuteProject, deductCredit, estimateProjectCost, PRICING, BillingState, CostEstimate } from "@/lib/billing";
import Link from "next/link";

export default function ProposalPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    proposalGet(id)
      .then((p) => {
        setProposal(p);
        setCostEstimate(estimateProjectCost(p.estimated_hours));
      })
      .catch((e: Error) => setError(e.message));
    setBilling(getState());
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
      </div>
    );
  }

  if (!proposal || !billing || !costEstimate) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="typing" style={{ justifyContent: "center" }}><span /><span /><span /></div>
        <p style={{ marginTop: "1rem" }}>Loading proposal…</p>
      </div>
    );
  }

  const alreadyExecuted = billing.executedProjects.includes(id);
  const hasCredits = canExecuteProject(id, costEstimate.totalCredits);

  function handleExecute() {
    if (!costEstimate) return;
    setExecuting(true);
    try {
      deductCredit(id, costEstimate.totalCredits);
      router.push(`/status/${id}`);
    } catch {
      setExecuting(false);
    }
  }

  function fmtTokens(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  }

  return (
    <div className="container" style={{ padding: "3rem 1.5rem", maxWidth: 760, margin: "0 auto" }}>
      <span className="badge badge-violet" style={{ marginBottom: "1rem" }}>📄 Proposal</span>
      <h1 style={{ fontSize: "2rem", marginBottom: "2rem" }}>Your Project Proposal</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {/* Problem */}
        <div className="card">
          <h3 style={{ marginBottom: ".75rem", color: "#a78bfa" }}>Problem Statement</h3>
          <p style={{ color: "var(--text)", lineHeight: 1.7 }}>{proposal.problem_statement || "To be defined."}</p>
        </div>

        {/* Solution */}
        <div className="card">
          <h3 style={{ marginBottom: ".75rem", color: "#a78bfa" }}>Solution Overview</h3>
          <p style={{ color: "var(--text)", lineHeight: 1.7 }}>{proposal.solution_overview || "To be defined."}</p>
        </div>

        {/* Plan */}
        <div className="card">
          <h3 style={{ marginBottom: ".75rem", color: "#a78bfa" }}>Implementation Plan</h3>
          <p style={{ color: "var(--text)", lineHeight: 1.7 }}>{proposal.implementation_plan || "To be defined."}</p>
        </div>

        {/* Deliverables */}
        {proposal.deliverables.length > 0 && (
          <div className="card">
            <h3 style={{ marginBottom: ".75rem", color: "#a78bfa" }}>Deliverables</h3>
            <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: ".4rem" }}>
              {proposal.deliverables.map((d, i) => (
                <li key={i} style={{ color: "var(--text)", lineHeight: 1.6 }}>{d}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Timeline */}
        <div className="card">
          <h3 style={{ marginBottom: "1rem", color: "#a78bfa" }}>Timeline</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {[
              { label: "Estimated hours", value: `${proposal.estimated_hours}h` },
              { label: "Delivery ETA", value: `${proposal.delivery_eta_days} days` },
            ].map((row) => (
              <div key={row.label} className="card" style={{ padding: "1rem" }}>
                <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".25rem" }}>{row.label}</div>
                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#e2e8f0" }}>{row.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Credit CTA */}
        <div
          className="card"
          style={{ background: "linear-gradient(135deg, rgba(109,40,217,.15), rgba(168,85,247,.08))", borderColor: "rgba(109,40,217,.4)" }}
        >
          <h3 style={{ marginBottom: "1rem", color: "#e2e8f0" }}>Execution Cost</h3>

          {/* CPM breakdown table */}
          <div
            style={{
              background: "var(--surface-h)", border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)", overflow: "hidden", marginBottom: "1.25rem",
              fontSize: ".85rem",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Type", "Est. tokens", "Credits / 1M tokens", "Credits"].map((h) => (
                    <th key={h} style={{ padding: ".5rem .75rem", textAlign: "left", color: "var(--muted)", fontWeight: 500, fontSize: ".78rem" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: ".55rem .75rem", color: "var(--text)" }}>Input</td>
                  <td style={{ padding: ".55rem .75rem", color: "var(--muted)", fontFamily: "monospace" }}>{fmtTokens(costEstimate.inputTokens)}</td>
                  <td style={{ padding: ".55rem .75rem", color: "var(--muted)", fontFamily: "monospace" }}>{PRICING.inputPerMillion}</td>
                  <td style={{ padding: ".55rem .75rem", color: "#c4b5fd", fontFamily: "monospace", fontWeight: 600 }}>
                    {costEstimate.inputCredits.toFixed(2)}
                  </td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: ".55rem .75rem", color: "var(--text)" }}>Output</td>
                  <td style={{ padding: ".55rem .75rem", color: "var(--muted)", fontFamily: "monospace" }}>{fmtTokens(costEstimate.outputTokens)}</td>
                  <td style={{ padding: ".55rem .75rem", color: "var(--muted)", fontFamily: "monospace" }}>{PRICING.outputPerMillion}</td>
                  <td style={{ padding: ".55rem .75rem", color: "#c4b5fd", fontFamily: "monospace", fontWeight: 600 }}>
                    {costEstimate.outputCredits.toFixed(2)}
                  </td>
                </tr>
                <tr style={{ background: "rgba(109,40,217,.08)" }}>
                  <td style={{ padding: ".65rem .75rem", fontWeight: 700, color: "var(--text)" }}>Total</td>
                  <td style={{ padding: ".65rem .75rem", color: "var(--muted)", fontFamily: "monospace" }}>{fmtTokens(costEstimate.totalTokens)}</td>
                  <td style={{ padding: ".65rem .75rem", color: "var(--muted)", fontSize: ".75rem" }}>
                    blended {((costEstimate.inputCredits + costEstimate.outputCredits) / (costEstimate.totalTokens / 1_000_000)).toFixed(1)}
                  </td>
                  <td style={{ padding: ".65rem .75rem", color: "#a78bfa", fontFamily: "monospace", fontWeight: 700, fontSize: "1.05rem" }}>
                    {costEstimate.totalCredits}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p style={{ fontSize: ".75rem", color: "var(--muted)", marginBottom: "1.25rem" }}>
            Estimated from {proposal.estimated_hours}h × {(PRICING.tokensPerHour / 1000).toFixed(0)}K tokens/hr ·
            {" "}{Math.round(PRICING.inputRatio * 100)}% input / {Math.round((1 - PRICING.inputRatio) * 100)}% output.
            Based on estimate — actual usage may vary.
          </p>

          {/* Balance vs cost */}
          <div style={{ display: "flex", gap: ".75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
            <div className="card" style={{ padding: ".75rem 1rem", flex: 1, minWidth: 130 }}>
              <div style={{ fontSize: ".75rem", color: "var(--muted)", marginBottom: ".2rem" }}>This project</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#a78bfa" }}>
                {costEstimate.totalCredits} credits
              </div>
            </div>
            <div className="card" style={{ padding: ".75rem 1rem", flex: 1, minWidth: 130 }}>
              <div style={{ fontSize: ".75rem", color: "var(--muted)", marginBottom: ".2rem" }}>Your balance</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: billing.credits >= costEstimate.totalCredits ? "#4ade80" : "#f87171" }}>
                {billing.credits} credits
              </div>
            </div>
          </div>

          {alreadyExecuted ? (
            <>
              <p style={{ fontSize: ".85rem", color: "#94a3b8", marginBottom: "1.25rem" }}>
                This project has already been executed.
              </p>
              <Link href={`/status/${id}`} className="btn btn-outline" style={{ width: "100%", justifyContent: "center", padding: ".9rem" }}>
                View Status →
              </Link>
            </>
          ) : hasCredits ? (
            <button
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center", padding: ".9rem", opacity: executing ? .7 : 1 }}
              onClick={handleExecute}
              disabled={executing}
            >
              {executing ? "Starting…" : `Execute Project — ${costEstimate.totalCredits} credits →`}
            </button>
          ) : (
            <>
              <p style={{ fontSize: ".85rem", color: "#f87171", marginBottom: "1.25rem" }}>
                Insufficient credits. You need {costEstimate.totalCredits} but have {billing.credits}.
              </p>
              <Link href="/billing" className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: ".9rem" }}>
                Get More Credits →
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
