import Link from "next/link";

const tiers = [
  {
    id: "starter",
    name: "Starter",
    price: 49,
    credits: 30,
    highlight: false,
    perks: ["30 credits / month", "All 6 AI agents", "Real-time task tracker", "Email support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 149,
    credits: 100,
    highlight: true,
    perks: ["100 credits / month", "All 6 AI agents", "Priority queue", "Slack integration", "Priority support"],
  },
  {
    id: "business",
    name: "Business",
    price: 399,
    credits: 300,
    highlight: false,
    perks: ["300 credits / month", "All 6 AI agents", "Dedicated agent pool", "SLA guarantee", "Dedicated account manager"],
  },
];

const testimonials = [
  {
    quote: "We shipped a working internal dashboard in four days. Our usual dev shop would have quoted six weeks. I was stunned.",
    name: "Jordan Mercer",
    title: "CTO, Fieldline Logistics",
  },
  {
    quote: "The transparency is unlike anything I've seen — you can watch every agent decision in real time. It's like having a glass-box dev team.",
    name: "Priya Shankar",
    title: "Head of Product, NovaBridge",
  },
  {
    quote: "We used the Pro tier for three back-to-back projects. Burned through credits fast, but the ROI was obvious by week two.",
    name: "Marcus Oyelaran",
    title: "Founder, Greycoast Labs",
  },
  {
    quote: "Skeptical at first — a swarm of AI agents sounded like a buzzword. By the time the demo landed I was sold.",
    name: "Dana Whitfield",
    title: "VP Engineering, Tandem Health",
  },
];

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
    icon: "💳",
    title: "Flexible Credits",
    desc: "Subscribe for a monthly credit allowance or top up as you go. No unlimited tier — just what you need.",
  },
  {
    icon: "📊",
    title: "Full Transparency",
    desc: "Real-time task tracker shows exactly what each agent is doing, every step of the way.",
  },
];

const steps = [
  { n: "01", title: "Consult", desc: "Chat with our AI Sales agent. Describe your project in plain English." },
  { n: "02", title: "Proposal", desc: "Receive a detailed proposal with scope, delivery estimate, and timeline." },
  { n: "03", title: "Credits", desc: "Use one credit from your subscription allowance to kick off the agent swarm." },
  { n: "04", title: "Delivered", desc: "Agents execute, QA reviews, and you receive a live demo when it's done." },
];

/**
 * Marketing landing page that presents the AI consulting agency with a hero section,
 * feature highlights, how-it-works steps, subscription pricing tiers, client testimonials, and a CTA banner.
 *
 * @returns {JSX.Element} The full landing page layout including footer.
 */
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
            delivery. Subscription credits. No surprises.
          </p>
          <div style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/consult" className="btn btn-primary" style={{ fontSize: "1.05rem", padding: "0.9rem 2rem" }}>
              Start Free Consultation →
            </Link>
            <Link href="#how" className="btn btn-outline">
              How it works
            </Link>
            <Link href="#pricing" className="btn btn-outline">
              Pricing
            </Link>
          </div>
          <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#475569" }}>
            Sign up in one click with GitHub — no forms, no passwords.
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

      {/* ── Pricing ──────────────────────────────────────── */}
      <section id="pricing" style={{ padding: "5rem 0" }}>
        <div className="container">
          <h2 style={{ textAlign: "center", marginBottom: "0.5rem" }}>Simple, transparent pricing</h2>
          <p style={{ textAlign: "center", marginBottom: "3rem", color: "#94a3b8" }}>
            Subscribe for a monthly credit allowance. Top up any time with credit packs.
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1.25rem",
              alignItems: "start",
            }}
          >
            {tiers.map((t) => (
              <div
                key={t.id}
                className="card fade-up"
                style={{
                  position: "relative",
                  borderColor: t.highlight ? "rgba(168,85,247,.6)" : undefined,
                  background: t.highlight
                    ? "linear-gradient(135deg, rgba(109,40,217,.18), rgba(168,85,247,.08))"
                    : undefined,
                }}
              >
                {t.highlight && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-1px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      background: "linear-gradient(135deg,#a855f7,#ec4899)",
                      borderRadius: "0 0 8px 8px",
                      padding: "0.2rem 0.9rem",
                      fontSize: "0.72rem",
                      fontWeight: 700,
                      letterSpacing: "0.05em",
                      color: "#fff",
                      whiteSpace: "nowrap",
                    }}
                  >
                    MOST POPULAR
                  </div>
                )}
                <h3 style={{ marginBottom: "0.25rem", marginTop: t.highlight ? "0.75rem" : undefined }}>{t.name}</h3>
                <div style={{ marginBottom: "1.25rem" }}>
                  <span
                    style={{
                      fontSize: "2.5rem",
                      fontWeight: 800,
                      background: "var(--violet-g)",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                      backgroundClip: "text",
                    }}
                  >
                    ${t.price}
                  </span>
                  <span style={{ color: "#64748b", fontSize: "0.9rem" }}> / mo</span>
                </div>
                <ul style={{ listStyle: "none", padding: 0, margin: "0 0 1.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {t.perks.map((perk) => (
                    <li key={perk} style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
                      <span style={{ color: "#a855f7", marginRight: "0.5rem" }}>✓</span>
                      {perk}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/consult"
                  className={t.highlight ? "btn btn-primary" : "btn btn-outline"}
                  style={{ display: "block", textAlign: "center" }}
                >
                  Get started →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────── */}
      <section style={{ padding: "5rem 0" }}>
        <div className="container">
          <h2 style={{ textAlign: "center", marginBottom: "0.5rem" }}>What clients are saying</h2>
          <p style={{ textAlign: "center", marginBottom: "3rem", color: "#94a3b8" }}>
            Real results from teams who shipped with Agent-Puter.
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {testimonials.map((t) => (
              <div key={t.name} className="card fade-up">
                <p
                  style={{
                    fontSize: "0.95rem",
                    color: "#cbd5e1",
                    lineHeight: 1.65,
                    marginBottom: "1.25rem",
                    fontStyle: "italic",
                  }}
                >
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "#e2e8f0" }}>{t.name}</div>
                  <div style={{ fontSize: "0.8rem", color: "#64748b" }}>{t.title}</div>
                </div>
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
