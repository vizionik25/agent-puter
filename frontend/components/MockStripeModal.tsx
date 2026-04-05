"use client";

import { useState } from "react";

interface Props {
  title: string;
  amount: number;
  description: string;
  onSuccess: () => void;
  onCancel: () => void;
}

type State = "idle" | "processing" | "success";

export default function MockStripeModal({ title, amount, description, onSuccess, onCancel }: Props) {
  const [state, setState] = useState<State>("idle");

  function handlePay() {
    setState("processing");
    setTimeout(() => {
      setState("success");
      setTimeout(() => onSuccess(), 800);
    }, 1500);
  }

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,.75)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "1rem",
      }}
      onClick={(e) => { if (e.target === e.currentTarget && state === "idle") onCancel(); }}
    >
      <div
        className="card"
        style={{ width: "100%", maxWidth: 440, padding: "2rem", position: "relative" }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: ".5rem", marginBottom: ".25rem" }}>
          <span style={{ fontSize: "1rem" }}>🔒</span>
          <span style={{ fontWeight: 700, fontSize: "1.05rem", color: "var(--text)" }}>Secure Checkout</span>
        </div>
        <p style={{ fontSize: ".75rem", color: "var(--muted)", marginBottom: "1.5rem" }}>
          Powered by <span style={{ color: "#635bff", fontWeight: 600 }}>stripe</span>
        </p>

        {/* Order summary */}
        <div
          style={{
            padding: ".75rem 1rem", borderRadius: "var(--radius-sm)",
            background: "var(--surface-h)", border: "1px solid var(--border)",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--text)" }}>{title}</div>
          <div style={{ fontSize: ".85rem", color: "var(--muted)", marginTop: ".2rem" }}>{description}</div>
          <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#a78bfa", marginTop: ".5rem" }}>
            {fmt(amount)}
          </div>
        </div>

        {state === "success" ? (
          <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: ".5rem" }}>✅</div>
            <div style={{ fontWeight: 600, color: "#4ade80" }}>Payment successful!</div>
          </div>
        ) : (
          <>
            {/* Card fields (read-only prefilled — mock) */}
            <div style={{ display: "flex", flexDirection: "column", gap: ".75rem", marginBottom: "1.5rem" }}>
              <div>
                <label style={{ fontSize: ".8rem", color: "var(--muted)", display: "block", marginBottom: ".3rem" }}>
                  Card number
                </label>
                <input
                  readOnly
                  value="4242 4242 4242 4242"
                  style={inputStyle}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".75rem" }}>
                <div>
                  <label style={{ fontSize: ".8rem", color: "var(--muted)", display: "block", marginBottom: ".3rem" }}>
                    Expiry
                  </label>
                  <input readOnly value="12 / 28" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: ".8rem", color: "var(--muted)", display: "block", marginBottom: ".3rem" }}>
                    CVC
                  </label>
                  <input readOnly value="424" style={inputStyle} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: ".8rem", color: "var(--muted)", display: "block", marginBottom: ".3rem" }}>
                  Name on card
                </label>
                <input
                  defaultValue="Test User"
                  disabled={state === "processing"}
                  style={inputStyle}
                />
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: ".75rem" }}>
              <button
                className="btn btn-primary"
                style={{ flex: 1, padding: ".75rem", justifyContent: "center", opacity: state === "processing" ? .7 : 1 }}
                onClick={handlePay}
                disabled={state === "processing"}
              >
                {state === "processing" ? (
                  <span style={{ display: "flex", alignItems: "center", gap: ".5rem" }}>
                    <span
                      style={{
                        width: 14, height: 14, border: "2px solid rgba(255,255,255,.3)",
                        borderTopColor: "#fff", borderRadius: "50%",
                        animation: "spin 0.6s linear infinite", display: "inline-block",
                      }}
                    />
                    Processing…
                  </span>
                ) : (
                  `Pay ${fmt(amount)}`
                )}
              </button>
              <button
                className="btn btn-outline"
                style={{ padding: ".75rem 1.25rem" }}
                onClick={onCancel}
                disabled={state === "processing"}
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: ".6rem .75rem",
  background: "var(--surface-h)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--text)",
  fontSize: ".9rem",
  fontFamily: "inherit",
  boxSizing: "border-box",
};
