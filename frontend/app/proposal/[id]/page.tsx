"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { proposalGet, Proposal } from "@/lib/api";
import Link from "next/link";

export default function ProposalPage() {
  const { id } = useParams<{ id: string }>();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    proposalGet(id)
      .then(setProposal)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="typing" style={{ justifyContent: "center" }}><span /><span /><span /></div>
        <p style={{ marginTop: "1rem" }}>Loading proposal…</p>
      </div>
    );
  }

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

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

        {/* Pricing */}
        <div
          className="card"
          style={{ background: "linear-gradient(135deg, rgba(109,40,217,.15), rgba(168,85,247,.08))", borderColor: "rgba(109,40,217,.4)" }}
        >
          <h3 style={{ marginBottom: "1rem", color: "#e2e8f0" }}>Pricing & Timeline</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            {[
              { label: "Estimated hours", value: `${proposal.estimated_hours}h` },
              { label: "Delivery ETA", value: `${proposal.delivery_eta_days} days` },
              { label: "Total Price", value: fmt(proposal.total_price_usd) },
              { label: "20% Deposit", value: fmt(proposal.deposit_amount_usd) },
            ].map((row) => (
              <div key={row.label} className="card" style={{ padding: "1rem" }}>
                <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".25rem" }}>{row.label}</div>
                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#e2e8f0" }}>{row.value}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: ".85rem", color: "#94a3b8", marginBottom: "1.5rem" }}>{proposal.payment_structure}</p>
          <Link href={`/pay/${id}/deposit`} className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: ".9rem" }}>
            Pay {fmt(proposal.deposit_amount_usd)} Deposit to Start →
          </Link>
        </div>
      </div>
    </div>
  );
}
