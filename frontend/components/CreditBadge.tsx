"use client";

import { useEffect, useState } from "react";
import { getCredits, getTier } from "@/lib/billing";
import Link from "next/link";

export default function CreditBadge() {
  const [credits, setCredits] = useState<number | null>(null);
  const [tierName, setTierName] = useState<string>("");

  useEffect(() => {
    function read() {
      setCredits(getCredits());
      setTierName(getTier().name);
    }
    read();
    // Refresh when the tab regains focus (e.g. after billing page visit)
    window.addEventListener("focus", read);
    return () => window.removeEventListener("focus", read);
  }, []);

  if (credits === null) return null;

  return (
    <Link
      href="/billing"
      style={{
        display: "flex", alignItems: "center", gap: ".4rem",
        padding: ".4rem .85rem",
        borderRadius: "var(--radius-sm)",
        border: "1px solid rgba(168,85,247,.35)",
        background: "rgba(109,40,217,.12)",
        color: "#c4b5fd",
        fontSize: ".85rem",
        fontWeight: 500,
        textDecoration: "none",
        transition: "background .2s",
      }}
    >
      <span>⚡</span>
      <span>{credits} credit{credits !== 1 ? "s" : ""}</span>
      <span style={{ color: "var(--muted)", fontSize: ".75rem" }}>· {tierName}</span>
    </Link>
  );
}
