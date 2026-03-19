/**
 * app/pay/[id]/final/page.tsx — Stripe final balance payment page (80%).
 *
 * On mount, simultaneously calls:
 *   - POST /api/payments/final     → receives Stripe client_secret
 *     (backend returns 400 if deposit is not yet paid)
 *   - GET  /api/projects/{id}/proposal → receives final_amount_usd
 *   - GET  /api/payments/{id}/status   → checks deposit_paid flag
 *
 * If deposit_paid is false, renders a redirect card to /pay/{id}/deposit
 * rather than the payment form.
 *
 * FinalForm — inner component that owns Stripe hooks and submit logic.
 * FinalPayPage — outer component that owns data fetching and guard logic.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { finalIntent, proposalGet, Proposal, paymentStatus } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "pk_test_placeholder");

function FinalForm({ projectId, proposal }: { projectId: string; proposal: Proposal }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "processing" | "error">("idle");
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
      router.push(`/status/${projectId}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="card" style={{ background: "rgba(34,197,94,.08)", borderColor: "rgba(34,197,94,.3)", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "var(--muted)", fontSize: ".9rem" }}>Final balance (80%)</span>
          <span style={{ fontSize: "1.5rem", fontWeight: 700, color: "#e2e8f0" }}>{fmt(proposal.final_amount_usd)}</span>
        </div>
        <p style={{ fontSize: ".8rem", marginTop: ".5rem", color: "#86efac" }}>
          ✅ Pay to receive the complete deliverable package.
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
        {status === "processing" ? "Processing…" : `Pay ${fmt(proposal.final_amount_usd)} & Receive Delivery →`}
      </button>

      <p style={{ fontSize: ".8rem", color: "var(--muted)", textAlign: "center" }}>
        🔒 Secured by Stripe. We never see your card details.
      </p>
    </form>
  );
}

export default function FinalPayPage() {
  const { id } = useParams<{ id: string }>();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [depositPaid, setDepositPaid] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([finalIntent({ project_id: id }), proposalGet(id), paymentStatus(id)])
      .then(([intent, p, ps]) => {
        setClientSecret(intent.client_secret);
        setProposal(p);
        setDepositPaid(ps.deposit_paid);
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#f87171" }}>⚠️ {error}</p>
        <Link href={`/pay/${id}/deposit`} className="btn btn-primary" style={{ marginTop: "1rem" }}>
          Pay deposit first
        </Link>
      </div>
    );
  }

  if (depositPaid === false) {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p style={{ color: "#fbbf24", marginBottom: "1rem" }}>⚠️ Please pay the deposit before the final payment.</p>
        <Link href={`/pay/${id}/deposit`} className="btn btn-primary">Pay deposit →</Link>
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
      <span className="badge badge-green" style={{ marginBottom: "1rem" }}>✅ Final Payment</span>
      <h1 style={{ fontSize: "1.8rem", marginBottom: ".5rem" }}>Complete your payment</h1>
      <p style={{ marginBottom: "2rem" }}>You've reviewed the demo. Pay the 80% balance to receive the full delivery.</p>

      <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: "night", variables: { colorPrimary: "#22c55e" } } }}>
        <FinalForm projectId={id} proposal={proposal} />
      </Elements>
    </div>
  );
}
