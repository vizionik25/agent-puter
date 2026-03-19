import Link from "next/link";

const features = [
  {
    icon: "🤖",
    title: "Autonomous Swarm",
    desc: "A team of specialised AI agents — CEO, PM, Engineer, QA — collaborate to deliver your project.",
  },
  {
    icon: "⚡",
    title: "Lightning Fast",
    desc: "From consultation to working deliverable in days, not months. No sprint planning theatre.",
  },
  {
    icon: "🔒",
    title: "Pay on Results",
    desc: "20% deposit, then review a live demo before you pay the remaining 80%. Zero risk.",
  },
  {
    icon: "📊",
    title: "Full Transparency",
    desc: "Real-time task tracker shows exactly what each agent is doing, every step of the way.",
  },
];

const steps = [
  { n: "01", title: "Consult", desc: "Chat with our AI Sales agent. Describe your project in plain English." },
  { n: "02", title: "Proposal", desc: "Receive a detailed proposal with scope, delivery estimate, and fixed price." },
  { n: "03", title: "Deposit", desc: "Pay a 20% non-refundable deposit to kick off the agent swarm." },
  { n: "04", title: "Demo & Pay", desc: "Review a live demo. Happy? Pay the 80% balance and receive delivery." },
];

export default function LandingPage() {
  return (
    <div>
      {/* ── Hero ─────────────────────────────────────────── */}
      <section
        style={{
          position: "relative",
          overflow: "hidden",
          padding: "6rem 0 5rem",
          textAlign: "center",
        }}
      >
        <div
          className="hero-orb"
          style={{ left: "50%", top: "0", transform: "translateX(-50%)" }}
        />
        <div className="container" style={{ position: "relative", zIndex: 1 }}>
          <span className="badge badge-violet" style={{ marginBottom: "1.5rem" }}>
            🚀 Autonomous AI Agency — Now Open
          </span>
          <h1 style={{ marginBottom: "1.5rem" }}>
            Your Project,{" "}
            <span
              style={{
                background: "linear-gradient(135deg,#a855f7,#ec4899)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Delivered by AI
            </span>
          </h1>
          <p
            style={{
              fontSize: "1.2rem",
              maxWidth: "600px",
              margin: "0 auto 2.5rem",
              color: "#94a3b8",
            }}
          >
            A swarm of specialised AI agents handles everything — from discovery to
            delivery. Fixed pricing. Pay on results.
          </p>
          <div style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/consult" className="btn btn-primary" style={{ fontSize: "1.05rem", padding: "0.9rem 2rem" }}>
              Start Free Consultation →
            </Link>
            <Link href="#how" className="btn btn-outline">
              How it works
            </Link>
          </div>
          <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#475569" }}>
            No sign-up required. Talk to the AI now.
          </p>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────── */}
      <section style={{ padding: "4rem 0" }}>
        <div className="container">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {features.map((f) => (
              <div key={f.title} className="card fade-up">
                <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>{f.icon}</div>
                <h3 style={{ marginBottom: "0.5rem" }}>{f.title}</h3>
                <p style={{ fontSize: "0.9rem" }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────── */}
      <section id="how" style={{ padding: "5rem 0" }}>
        <div className="container">
          <h2 style={{ textAlign: "center", marginBottom: "0.5rem" }}>How it works</h2>
          <p style={{ textAlign: "center", marginBottom: "3rem" }}>
            From brief to delivery — four simple steps.
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {steps.map((s) => (
              <div key={s.n} className="card" style={{ position: "relative" }}>
                <div
                  style={{
                    fontSize: "2.5rem",
                    fontWeight: 800,
                    background: "var(--violet-g)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                    lineHeight: 1,
                    marginBottom: "1rem",
                  }}
                >
                  {s.n}
                </div>
                <h3 style={{ marginBottom: "0.5rem" }}>{s.title}</h3>
                <p style={{ fontSize: "0.9rem" }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA banner ────────────────────────────────────── */}
      <section style={{ padding: "5rem 0" }}>
        <div className="container">
          <div
            className="card"
            style={{
              textAlign: "center",
              padding: "3rem 2rem",
              background: "linear-gradient(135deg, rgba(109,40,217,.15), rgba(168,85,247,.08))",
              borderColor: "rgba(109,40,217,.4)",
            }}
          >
            <h2 style={{ marginBottom: "1rem", color: "#e2e8f0" }}>
              Ready to get started?
            </h2>
            <p style={{ marginBottom: "2rem" }}>
              Chat with our AI consultant — free, instant, no commitment.
            </p>
            <Link href="/consult" className="btn btn-primary" style={{ padding: "0.9rem 2.5rem", fontSize: "1.05rem" }}>
              Start Consultation →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "2rem 0", textAlign: "center" }}>
        <p style={{ fontSize: "0.85rem" }}>
          © 2026 SwarmAI — Autonomous AI Consulting Agency
        </p>
      </footer>
    </div>
  );
}
