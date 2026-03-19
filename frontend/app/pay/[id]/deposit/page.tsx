/**
 * app/pay/[id]/deposit/page.tsx — Stripe deposit payment page (20%).
 *
 * On mount, simultaneously calls:
 *   - POST /api/payments/deposit  → receives Stripe client_secret
 *   - GET  /api/projects/{id}/proposal → receives deposit_amount_usd
 *
 * Renders a Stripe Elements form (PaymentElement) pre-loaded with the
 * client_secret. On confirmation, Stripe redirects to /status/{id}
 * via confirmParams.return_url.
 *
 * DepositForm — inner component that owns Stripe hooks and submit logic.
 * DepositPage — outer component that owns data fetching and passes props down.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { depositIntent, proposalGet, Proposal } from "@/lib/api";
import { useRouter } from "next/navigation";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "pk_test_placeholder");

function DepositForm({ projectId, proposal }: { projectId: string; proposal: Proposal }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "processing" | "success" | "error">("idle");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setStatus("processing");
    setErrMsg(null);
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: `${window.location.origin}/status/${projectId}` },
    });
    if (error) {
      setErrMsg(error.message ?? "Payment failed");
      setStatus("error");
    } else {
      setStatus("success");
      router.push(`/status/${projectId}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="card" style={{ background: "rgba(109,40,217,.08)", borderColor: "rgba(109,40,217,.3)", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "var(--muted)", fontSize: ".9rem" }}>Deposit (20%)</span>
          <span style={{ fontSize: "1.5rem", fontWeight: 700, color: "#e2e8f0" }}>{fmt(proposal.deposit_amount_usd)}</span>
        </div>
        <p style={{ fontSize: ".8rem", marginTop: ".5rem", color: "#ef4444" }}>
          ⚠️ This deposit is non-refundable once work begins.
        </p>
      </div>

      <div className="card">
        <PaymentElement />
      </div>

      {errMsg && <p style={{ color: "#f87171", fontSize: ".9rem" }}>{errMsg}</p>}

      <button
        className="btn btn-primary"
        type="submit"
        disabled={!stripe || status === "processing"}
        style={{ padding: ".9rem", fontSize: "1rem" }}
      >
        {status === "processing" ? "Processing…" : `Pay ${fmt(proposal.deposit_amount_usd)} →`}
      </button>

      <p style={{ fontSize: ".8rem", color: "var(--muted)", textAlign: "center" }}>
        🔒 Secured by Stripe. We never see your card details.
      </p>
    </form>
  );
}

export default function DepositPage() {
  const { id } = useParams<{ id: string }>();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([depositIntent({ project_id: id }), proposalGet(id)])
      .then(([intent, p]) => {
        setClientSecret(intent.client_secret);
        setProposal(p);
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
      </div>
    );
  }

  if (!clientSecret || !proposal) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <div className="typing" style={{ justifyContent: "center" }}><span /><span /><span /></div>
        <p style={{ marginTop: "1rem" }}>Loading payment…</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: "3rem 1.5rem", maxWidth: 560, margin: "0 auto" }}>
      <span className="badge badge-violet" style={{ marginBottom: "1rem" }}>💳 Deposit</span>
      <h1 style={{ fontSize: "1.8rem", marginBottom: ".5rem" }}>Pay your deposit</h1>
      <p style={{ marginBottom: "2rem" }}>20% to kick off the agent swarm. The remaining 80% is due after demo review.</p>

      <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: "night", variables: { colorPrimary: "#7c3aed" } } }}>
        <DepositForm projectId={id} proposal={proposal} />
      </Elements>
    </div>
  );
}
