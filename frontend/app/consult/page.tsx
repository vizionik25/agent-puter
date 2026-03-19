"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { consultStart, consultMessage, ConsultMessage } from "@/lib/api";
import { useRouter } from "next/navigation";

interface Bubble {
  role: "user" | "agent";
  content: string;
}

type Phase = "intro" | "chat";

export default function ConsultPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("intro");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [firstMsg, setFirstMsg] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [bubbles, loading]);

  async function handleStart(e: FormEvent) {
    e.preventDefault();
    if (!name || !email || !firstMsg) return;
    setLoading(true);
    setError(null);
    try {
      const res = await consultStart({ client_name: name, client_email: email, initial_message: firstMsg });
      setSessionId(res.session.id);
      setProjectId(res.session.project_id);
      setBubbles([
        { role: "user", content: firstMsg },
        { role: "agent", content: res.reply },
      ]);
      setPhase("chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || !sessionId) return;
    const msg = input.trim();
    setInput("");
    setBubbles((b) => [...b, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const res = await consultMessage(sessionId, { message: msg });
      setProjectId(res.session.project_id);
      setBubbles((b) => [...b, { role: "agent", content: res.reply }]);
      if (res.session.project_id && res.session.status === "complete") {
        setTimeout(() => router.push(`/proposal/${res.session.project_id}`), 1200);
      }
    } catch (err: unknown) {
      setBubbles((b) => [...b, { role: "agent", content: "⚠️ Connection error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  }

  if (phase === "intro") {
    return (
      <div className="container" style={{ padding: "4rem 1.5rem", maxWidth: 560, margin: "0 auto" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>Start your consultation</h1>
        <p style={{ marginBottom: "2rem" }}>
          Tell our AI Sales agent about your project. Takes 2 minutes.
        </p>
        <form onSubmit={handleStart} className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ fontSize: ".85rem", color: "var(--muted)", display: "block", marginBottom: ".4rem" }}>Your name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" required />
          </div>
          <div>
            <label style={{ fontSize: ".85rem", color: "var(--muted)", display: "block", marginBottom: ".4rem" }}>Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jane@example.com" required />
          </div>
          <div>
            <label style={{ fontSize: ".85rem", color: "var(--muted)", display: "block", marginBottom: ".4rem" }}>Describe your project</label>
            <textarea className="input" value={firstMsg} onChange={(e) => setFirstMsg(e.target.value)} placeholder="I need a dashboard that tracks..." required rows={4} />
          </div>
          {error && <p style={{ color: "#f87171", fontSize: ".9rem" }}>{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Connecting…" : "Chat with AI →"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 65px)" }}>
      {/* Chat area */}
      <div
        className="scroll-area"
        style={{ flex: 1, padding: "2rem", display: "flex", flexDirection: "column", gap: "1rem", overflowY: "auto" }}
      >
        {bubbles.map((b, i) => (
          <div key={i} style={{ display: "flex", justifyContent: b.role === "user" ? "flex-end" : "flex-start" }}>
            {b.role === "agent" && (
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--violet-g)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: ".9rem", marginRight: ".5rem", flexShrink: 0 }}>
                🤖
              </div>
            )}
            <div className={`chat-bubble ${b.role === "agent" ? "bubble-agent" : "bubble-user"}`}>
              {b.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: ".5rem" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--violet-g)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: ".9rem" }}>🤖</div>
            <div className="chat-bubble bubble-agent" style={{ padding: ".75rem 1rem" }}>
              <div className="typing"><span /><span /><span /></div>
            </div>
          </div>
        )}
        {projectId && (
          <div className="card" style={{ textAlign: "center", borderColor: "rgba(109,40,217,.5)", background: "rgba(109,40,217,.1)" }}>
            <p style={{ color: "var(--text)", marginBottom: ".75rem" }}>✅ Project created! Your proposal is ready.</p>
            <a href={`/proposal/${projectId}`} className="btn btn-primary">View Proposal →</a>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSend}
        style={{ padding: "1rem 2rem", borderTop: "1px solid var(--border)", display: "flex", gap: ".75rem", background: "rgba(7,9,15,.9)", backdropFilter: "blur(12px)" }}
      >
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()} style={{ padding: ".75rem 1.5rem" }}>
          Send
        </button>
      </form>
    </div>
  );
}
