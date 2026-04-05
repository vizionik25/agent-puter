/**
 * app/consult/page.tsx — Client consultation chat interface.
 *
 * Two-phase flow:
 *   1. "intro" — Collects client_name, client_email, and initial project description.
 *      Calls POST /api/consult/start → receives session_id + first Sales Agent reply.
 *   2. "chat"  — Real-time streaming chat via POST /api/consult/{id}/stream (SSE).
 *      Falls back to POST /api/consult/{id}/message if streaming fails.
 *      When the agent decides the session is complete (status="complete"),
 *      POST /api/consult/{id}/complete is called automatically to trigger the
 *      agency loop (CEO → PM → Engineer → QA) and the user is redirected to
 *      /proposal/{project_id}.
 */
"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { consultStart, consultMessage, consultComplete, consultStream } from "@/lib/api";
import { useRouter } from "next/navigation";

interface Bubble {
  role: "user" | "agent";
  content: string;
}

type Phase = "intro" | "chat";

/**
 * Two-phase consultation chat page: an intro form collects client name, email, and initial description,
 * then transitions to a streaming chat with the AI Sales agent that auto-redirects to the proposal on completion.
 *
 * @returns {JSX.Element} Either the intro form or the full-height chat interface.
 */
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
      setSessionId(res.session_id);
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

    // Add empty agent bubble that we'll fill in chunk by chunk
    setBubbles((b) => [...b, { role: "agent", content: "" }]);

    try {
      let streamDone = false;
      try {
        await consultStream(sessionId, msg, (chunk) => {
          setBubbles((b) => {
            const updated = [...b];
            updated[updated.length - 1] = {
              role: "agent",
              content: updated[updated.length - 1].content + chunk,
            };
            return updated;
          });
        });
        streamDone = true;
      } catch {
        // Streaming not available — fall back to non-streaming
        setBubbles((b) => b.slice(0, -1)); // remove the empty agent bubble
        const res = await consultMessage(sessionId, { message: msg });
        setBubbles((b) => [...b, { role: "agent", content: res.reply }]);
        streamDone = true;
      }

      if (streamDone) {
        // Check if session should complete
        try {
          const completed = await consultComplete(sessionId);
          if (completed.project_id) {
            setProjectId(completed.project_id);
            setTimeout(() => router.push(`/proposal/${completed.project_id}`), 1200);
          }
        } catch {
          // Session not yet ready to complete — that's fine
        }
      }
    } catch (err: unknown) {
      setBubbles((b) => {
        const updated = [...b];
        updated[updated.length - 1] = { role: "agent", content: "⚠️ Connection error. Please try again." };
        return updated;
      });
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
