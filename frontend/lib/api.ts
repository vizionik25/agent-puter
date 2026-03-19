const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9999";

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

export interface ConsultMessage {
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

export interface ConsultSession {
  id: string;
  client_name: string;
  client_email: string;
  messages: ConsultMessage[];
  project_id: string | null;
  status: "active" | "complete";
  created_at: string;
  updated_at: string;
}

export interface Proposal {
  problem_statement: string;
  solution_overview: string;
  implementation_plan: string;
  deliverables: string[];
  estimated_hours: number;
  delivery_eta_days: number;
  total_price_usd: number;
  deposit_amount_usd: number;
  final_amount_usd: number;
  payment_structure: string;
  created_at: string;
}

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  assigned_to: string | null;
  status: "pending" | "in_progress" | "review" | "done" | "failed";
  output: string | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  client_id: string;
  status: string;
  tasks: TaskItem[];
  total_price_usd: number;
  deposit_paid: boolean;
  final_paid: boolean;
  demo_url: string | null;
  proposal: Proposal | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentStatus {
  deposit_paid: boolean;
  final_paid: boolean;
}

// ── Consultation ─────────────────────────────────────────────────────────────

export const consultStart = (body: { client_name: string; client_email: string; initial_message: string }) =>
  req<{ session: ConsultSession; reply: string }>("/api/consult/start", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const consultMessage = (id: string, body: { message: string }) =>
  req<{ session: ConsultSession; reply: string }>(`/api/consult/${id}/message`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const consultGet = (id: string) =>
  req<ConsultSession>(`/api/consult/${id}`);

// ── Projects ─────────────────────────────────────────────────────────────────

export const projectGet = (id: string) =>
  req<Project>(`/api/projects/${id}`);

export const proposalGet = (id: string) =>
  req<Proposal>(`/api/projects/${id}/proposal`);

export const demoGet = (id: string) =>
  req<{ demo_url: string }>(`/api/projects/${id}/demo`);

// ── Payments ─────────────────────────────────────────────────────────────────

export const depositIntent = (body: { project_id: string }) =>
  req<{ client_secret: string; intent_id: string }>("/api/payments/deposit", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const finalIntent = (body: { project_id: string }) =>
  req<{ client_secret: string; intent_id: string }>("/api/payments/final", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const paymentStatus = (id: string) =>
  req<PaymentStatus>(`/api/payments/${id}/status`);
