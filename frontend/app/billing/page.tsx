/**
 * app/billing/page.tsx — Subscription & credit management.
 *
 * Shows the user's current plan, credit balance, upgrade options,
 * and credit pack purchases. All billing is client-side mock state
 * (no real Stripe subscriptions).
 */
"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getState, changeTier, purchasePack,
  TIERS, TIER_ORDER, CREDIT_PACKS,
  BillingState, TierId, daysUntilRenewal,
} from "@/lib/billing";
import MockStripeModal from "@/components/MockStripeModal";

interface ModalConfig {
  title: string;
  amount: number;
  description: string;
  onSuccess: () => void;
}

/**
 * Subscription and credit management page that shows the current plan, credit balance,
 * plan upgrade/downgrade options, one-time credit pack purchases, and a collapsible transaction ledger.
 *
 * @returns {JSX.Element} The billing dashboard with plan cards, credit packs, and ledger, or null while loading.
 */
export default function BillingPage() {
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [days, setDays] = useState(0);
  const [modal, setModal] = useState<ModalConfig | null>(null);
  const [showLedger, setShowLedger] = useState(false);

  const refresh = useCallback(() => {
    setBilling(getState());
    setDays(daysUntilRenewal());
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  if (!billing) return null;

  const currentTier = TIERS[billing.tierId];

  function openUpgradeModal(tierId: TierId) {
    const tier = TIERS[tierId];
    setModal({
      title: `${tier.name} Plan — $${tier.priceMonthly}/month`,
      amount: tier.priceMonthly,
      description: `${tier.creditsPerMonth} credits per month`,
      onSuccess: () => {
        changeTier(tierId);
        setModal(null);
        refresh();
      },
    });
  }

  function openPackModal(packId: string) {
    const pack = CREDIT_PACKS.find((p) => p.id === packId)!;
    setModal({
      title: `${pack.label} — $${pack.price}`,
      amount: pack.price,
      description: `Add ${pack.credits} credits to your account`,
      onSuccess: () => {
        purchasePack(packId);
        setModal(null);
        refresh();
      },
    });
  }

  function handleDowngrade() {
    if (window.confirm("Downgrade to the Free plan? You'll keep your current credits.")) {
      changeTier("free");
      refresh();
    }
  }

  return (
    <div className="container" style={{ padding: "3rem 1.5rem", maxWidth: 860, margin: "0 auto" }}>
      {modal && (
        <MockStripeModal
          title={modal.title}
          amount={modal.amount}
          description={modal.description}
          onSuccess={modal.onSuccess}
          onCancel={() => setModal(null)}
        />
      )}

      <span className="badge badge-violet" style={{ marginBottom: "1rem" }}>💳 Billing</span>
      <h1 style={{ fontSize: "2rem", marginBottom: "2rem" }}>Subscription & Credits</h1>

      {/* Current plan banner */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, rgba(109,40,217,.15), rgba(168,85,247,.08))",
          borderColor: "rgba(109,40,217,.4)",
          marginBottom: "2rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".25rem" }}>Current plan</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#e2e8f0" }}>{currentTier.name}</div>
            {currentTier.priceMonthly > 0 && (
              <div style={{ fontSize: ".9rem", color: "var(--muted)", marginTop: ".2rem" }}>
                ${currentTier.priceMonthly}/month · renews in {days} day{days !== 1 ? "s" : ""}
              </div>
            )}
            {currentTier.priceMonthly === 0 && (
              <div style={{ fontSize: ".9rem", color: "var(--muted)", marginTop: ".2rem" }}>
                Free plan · resets in {days} day{days !== 1 ? "s" : ""}
              </div>
            )}
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".25rem" }}>Credits remaining</div>
            <div style={{ fontSize: "2.5rem", fontWeight: 800, color: "#a78bfa", lineHeight: 1 }}>
              {billing.credits}
            </div>
            <div style={{ fontSize: ".8rem", color: "var(--muted)", marginTop: ".25rem" }}>
              of {currentTier.creditsPerMonth}/mo included
            </div>
          </div>
        </div>
      </div>

      {/* Plan tiers */}
      <h2 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Plans</h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "1rem",
          marginBottom: "2.5rem",
        }}
      >
        {TIER_ORDER.map((tierId) => {
          const tier = TIERS[tierId];
          const isCurrent = billing.tierId === tierId;
          const tierRank = TIER_ORDER.indexOf(tierId);
          const currentRank = TIER_ORDER.indexOf(billing.tierId);
          const isUpgrade = tierRank > currentRank;

          return (
            <div
              key={tierId}
              className="card"
              style={{
                borderColor: isCurrent ? "rgba(109,40,217,.6)" : "var(--border)",
                background: isCurrent ? "rgba(109,40,217,.08)" : "var(--surface)",
                position: "relative",
              }}
            >
              {isCurrent && (
                <span
                  className="badge badge-violet"
                  style={{ position: "absolute", top: "-.75rem", right: "1rem", fontSize: ".7rem" }}
                >
                  Current
                </span>
              )}
              <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--text)", marginBottom: ".25rem" }}>
                {tier.name}
              </div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#a78bfa", marginBottom: ".75rem" }}>
                {tier.priceMonthly === 0 ? "Free" : `$${tier.priceMonthly}`}
                {tier.priceMonthly > 0 && (
                  <span style={{ fontSize: ".75rem", color: "var(--muted)", fontWeight: 400 }}>/mo</span>
                )}
              </div>
              <ul style={{ paddingLeft: "1.1rem", marginBottom: "1rem", display: "flex", flexDirection: "column", gap: ".3rem" }}>
                {tier.features.map((f) => (
                  <li key={f} style={{ fontSize: ".8rem", color: "var(--muted)", lineHeight: 1.5 }}>{f}</li>
                ))}
              </ul>
              {!isCurrent && isUpgrade && (
                <button
                  className="btn btn-primary"
                  style={{ width: "100%", justifyContent: "center", padding: ".6rem", fontSize: ".85rem" }}
                  onClick={() => openUpgradeModal(tierId)}
                >
                  Upgrade
                </button>
              )}
              {!isCurrent && !isUpgrade && tierId !== "free" && (
                <button
                  className="btn btn-outline"
                  style={{ width: "100%", justifyContent: "center", padding: ".6rem", fontSize: ".85rem" }}
                  onClick={() => openUpgradeModal(tierId)}
                >
                  Switch
                </button>
              )}
              {!isCurrent && tierId === "free" && (
                <button
                  className="btn btn-outline"
                  style={{ width: "100%", justifyContent: "center", padding: ".6rem", fontSize: ".85rem", opacity: .7 }}
                  onClick={handleDowngrade}
                >
                  Downgrade
                </button>
              )}
              {isCurrent && (
                <div style={{ textAlign: "center", fontSize: ".8rem", color: "var(--muted)", padding: ".4rem 0" }}>
                  Active plan
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Credit packs */}
      <h2 style={{ fontSize: "1.25rem", marginBottom: ".5rem" }}>Top-up Credits</h2>
      <p style={{ fontSize: ".9rem", color: "var(--muted)", marginBottom: "1rem" }}>
        Need more? Buy additional credits — they never expire.
      </p>

      {billing.tierId === "free" ? (
        <div
          className="card"
          style={{ marginBottom: "2.5rem", borderColor: "rgba(251,191,36,.35)", background: "rgba(251,191,36,.06)" }}
        >
          <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
            <span style={{ fontSize: "1.5rem", flexShrink: 0 }}>🔒</span>
            <div>
              <div style={{ fontWeight: 600, color: "#fbbf24", marginBottom: ".35rem" }}>
                Paid subscription required
              </div>
              <p style={{ fontSize: ".9rem", color: "var(--muted)", margin: 0 }}>
                Credit pack purchases are available on Starter, Pro, and Business plans.
                Upgrade your plan above to unlock top-ups.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
            marginBottom: "2.5rem",
          }}
        >
          {CREDIT_PACKS.map((pack) => (
            <div key={pack.id} className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 800, color: "#a78bfa", marginBottom: ".25rem" }}>
                {pack.credits}
              </div>
              <div style={{ fontSize: ".85rem", color: "var(--muted)", marginBottom: ".75rem" }}>credits</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text)", marginBottom: "1rem" }}>
                ${pack.price}
              </div>
              <button
                className="btn btn-primary"
                style={{ width: "100%", justifyContent: "center", padding: ".6rem", fontSize: ".85rem" }}
                onClick={() => openPackModal(pack.id)}
              >
                Buy
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Transaction ledger */}
      <div className="card">
        <div
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
          onClick={() => setShowLedger((v) => !v)}
        >
          <h3 style={{ margin: 0 }}>Credit history</h3>
          <span style={{ color: "var(--muted)", fontSize: ".85rem" }}>{showLedger ? "Hide ▲" : "Show ▼"}</span>
        </div>
        {showLedger && (
          <div style={{ marginTop: "1rem", overflowX: "auto" }}>
            {billing.ledger.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: ".9rem" }}>No transactions yet.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".85rem" }}>
                <thead>
                  <tr>
                    {["Date", "Description", "Amount"].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left", padding: ".5rem .75rem",
                          borderBottom: "1px solid var(--border)",
                          color: "var(--muted)", fontWeight: 500, fontSize: ".8rem",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...billing.ledger].reverse().map((entry, i) => (
                    <tr key={i}>
                      <td style={{ padding: ".5rem .75rem", color: "var(--muted)", whiteSpace: "nowrap" }}>
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </td>
                      <td style={{ padding: ".5rem .75rem", color: "var(--text)" }}>
                        {entry.description}
                      </td>
                      <td
                        style={{
                          padding: ".5rem .75rem", fontWeight: 600, whiteSpace: "nowrap",
                          color: entry.amount >= 0 ? "#4ade80" : "#f87171",
                        }}
                      >
                        {entry.amount >= 0 ? `+${entry.amount}` : entry.amount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
