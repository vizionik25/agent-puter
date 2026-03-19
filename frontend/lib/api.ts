/**
 * lib/api.ts — Typed REST API client for the agent-puter backend.
 *
 * All requests are sent to the backend at NEXT_PUBLIC_API_URL (default:
 * http://localhost:9999). In development, next.config.ts proxies /api/* to
 * that address so same-origin rules are satisfied.
 *
 * Usage:
 *   import { consultStart, projectGet, depositIntent } from "@/lib/api";
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999";

/**
 * Generic fetch wrapper.
 * Throws an Error with a descriptive message on any non-2xx response.
 */
async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────────────────

/** A single message in a consultation transcript. */
export interface ConsultMessage {
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

/** Full consultation session object returned by GET /api/consult/{id}. */
export interface ConsultSession {
  id: string;
  client_name: string;
  client_email: string;
  messages: ConsultMessage[];
  /** Set after the agency loop has been kicked off via /complete. */
  project_id: string | null;
  status: "active" | "complete";
  created_at: string;
  updated_at: string;
}

// Flat response shapes returned directly by the backend

/** Response from POST /api/consult/start */
export interface ConsultStartResponse {
  session_id: string;
  reply: string;
  status: "active" | "complete";
}

/** Response from POST /api/consult/{id}/message */
export interface ConsultMessageResponse {
  reply: string;
  status: "active" | "complete";
  /** Present when the session transitions to complete. */
  project_id?: string | null;
}

/** Formal project proposal shown to the client before payment. */
export interface Proposal {
  problem_statement: string;
  solution_overview: string;
  implementation_plan: string;
  deliverables: string[];
  estimated_hours: number;
  delivery_eta_days: number;
  total_price_usd: number;
  /** 20% of total_price_usd. */
  deposit_amount_usd: number;
  /** 80% of total_price_usd. */
  final_amount_usd: number;
  payment_structure: string;
  created_at: string;
}

/** A single agent-executed task within a project. */
export interface TaskItem {
  id: string;
  title: string;
  description: string;
  /** Agent role assigned to this task (engineer, researcher, qa, …). */
  assigned_to: string | null;
  status: "pending" | "in_progress" | "review" | "done" | "failed";
  /** Final output produced by the execution agent. */
  output: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Full project object returned by GET /api/projects/{id}.
 * Includes tasks, payment flags, and embedded proposal when available.
 */
export interface Project {
  id: string;
  name: string;
  description: string;
  /** Client's email address (used as client_id). */
  client_id: string;
  /** Current lifecycle status: intake → planning → execution → qa → delivered. */
  status: string;
  tasks: TaskItem[];
  total_price_usd: number;
  deposit_paid: boolean;
  final_paid: boolean;
  /** Live demo URL — only populated by admin after delivery. */
  demo_url: string | null;
  /** Embedded proposal — null until /complete is called. */
  proposal: Proposal | null;
  created_at: string;
  updated_at: string;
}

/** Payment flags for a project, returned by GET /api/payments/{id}/status. */
export interface PaymentStatus {
  deposit_paid: boolean;
  final_paid: boolean;
}

// ── Consultation ─────────────────────────────────────────────────────────────

/**
 * Start a new consultation session.
 * Creates a session and gets the Sales Agent's opening greeting.
 *
 * @param body.client_name  - Client's display name.
 * @param body.client_email - Client's email (used as client_id throughout).
 * @param body.initial_message - Client's first project description.
 * @returns Flat response with session_id, first agent reply, and status.
 */
export const consultStart = (body: { client_name: string; client_email: string; initial_message: string }) =>
  req<ConsultStartResponse>("/api/consult/start", {
    method: "POST",
    body: JSON.stringify(body),
  });

/**
 * Send a follow-up message in an active consultation and get the agent's reply.
 *
 * @param id - Session ID from consultStart.
 * @param body.message - The user's message text.
 * @returns Agent reply, current session status, and project_id if session just completed.
 */
export const consultMessage = (id: string, body: { message: string }) =>
  req<ConsultMessageResponse>(`/api/consult/${id}/message`, {
    method: "POST",
    body: JSON.stringify(body),
  });

/**
 * Mark a consultation session as complete and kick off the agency loop.
 *
 * **Must be called explicitly** after the chat ends — this is what triggers
 * the CEO → PM → Engineer → QA chain and creates the Project + Proposal.
 *
 * @param id - Session ID from consultStart.
 * @returns session_id, the new project_id, and status="complete".
 */
export const consultComplete = (id: string) =>
  req<{ session_id: string; project_id: string; status: string }>(`/api/consult/${id}/complete`, {
    method: "POST",
  });

/**
 * Fetch the full consultation transcript and session metadata.
 *
 * @param id - Session ID.
 */
export const consultGet = (id: string) =>
  req<ConsultSession>(`/api/consult/${id}`);

// ── Projects ─────────────────────────────────────────────────────────────────

/**
 * Fetch project status, task list, and payment flags.
 * Poll this at intervals to show real-time progress on the status page.
 *
 * @param id - Project ID.
 */
export const projectGet = (id: string) =>
  req<Project>(`/api/projects/${id}`);

/**
 * Fetch the full proposal for a project.
 * Returns 404 until the agency loop has generated the proposal.
 *
 * @param id - Project ID.
 */
export const proposalGet = (id: string) =>
  req<Proposal>(`/api/projects/${id}/proposal`);

/**
 * Fetch the live demo URL for a project.
 * Returns 403 until the deposit is paid; 404 until the demo URL is set.
 *
 * @param id - Project ID.
 */
export const demoGet = (id: string) =>
  req<{ demo_url: string }>(`/api/projects/${id}/demo`);

// ── Payments ─────────────────────────────────────────────────────────────────

/**
 * Create a Stripe PaymentIntent for the 20% deposit.
 * Returns a client_secret to pass to stripe.confirmPayment().
 *
 * @param body.project_id - Project to pay the deposit for.
 */
export const depositIntent = (body: { project_id: string }) =>
  req<{ client_secret: string; intent_id: string }>("/api/payments/deposit", {
    method: "POST",
    body: JSON.stringify(body),
  });

/**
 * Create a Stripe PaymentIntent for the 80% final balance.
 * Returns 400 if the deposit has not been paid yet.
 *
 * @param body.project_id - Project to pay the final balance for.
 */
export const finalIntent = (body: { project_id: string }) =>
  req<{ client_secret: string; intent_id: string }>("/api/payments/final", {
    method: "POST",
    body: JSON.stringify(body),
  });

/**
 * Fetch the current payment status (deposit_paid + final_paid flags).
 *
 * @param id - Project ID.
 */
export const paymentStatus = (id: string) =>
  req<PaymentStatus>(`/api/payments/${id}/status`);
