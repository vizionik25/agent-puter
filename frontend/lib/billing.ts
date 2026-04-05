/**
 * lib/billing.ts — Client-side mock billing system.
 *
 * All state lives in localStorage under the key "agentputer_billing".
 * No backend calls are made — this is a frontend-only mock of the
 * subscription + credit model.
 *
 * Usage:
 *   import { getState, deductCredit, TIERS, CREDIT_PACKS } from "@/lib/billing";
 */

export type TierId = "free" | "starter" | "pro" | "business";

export interface Tier {
  id: TierId;
  name: string;
  priceMonthly: number;
  creditsPerMonth: number;
  features: string[];
}

export const TIERS: Record<TierId, Tier> = {
  free: {
    id: "free",
    name: "Free",
    priceMonthly: 0,
    creditsPerMonth: 0,
    features: ["0 credits / month", "Purchase credits to execute projects", "Project status tracking", "Community support"],
  },
  starter: {
    id: "starter",
    name: "Starter",
    priceMonthly: 49,
    creditsPerMonth: 30,
    features: ["30 credits / month", "All agent types", "Priority queue", "Email support"],
  },
  pro: {
    id: "pro",
    name: "Pro",
    priceMonthly: 149,
    creditsPerMonth: 100,
    features: ["100 credits / month", "All agent types", "Priority queue", "Dedicated Slack channel"],
  },
  business: {
    id: "business",
    name: "Business",
    priceMonthly: 399,
    creditsPerMonth: 300,
    features: ["300 credits / month", "All agent types", "SLA guarantee", "Dedicated account manager"],
  },
};

export const TIER_ORDER: TierId[] = ["free", "starter", "pro", "business"];

export interface CreditPack {
  id: string;
  credits: number;
  price: number;
  label: string;
}

export const CREDIT_PACKS: CreditPack[] = [
  { id: "pack_10",  credits: 10,  price: 12, label: "10 credits" },
  { id: "pack_30",  credits: 30,  price: 32, label: "30 credits" },
  { id: "pack_100", credits: 100, price: 99, label: "100 credits" },
];

export interface CreditLedgerEntry {
  type: "monthly_grant" | "pack_purchase" | "project_execution" | "tier_upgrade";
  amount: number;       // positive = credit, negative = debit
  description: string;
  projectId?: string;
  timestamp: string;    // ISO 8601
}

export interface BillingState {
  tierId: TierId;
  credits: number;
  cycleStart: string;          // ISO date of last monthly grant
  ledger: CreditLedgerEntry[];
  executedProjects: string[];  // idempotency: project IDs already charged
}

const STORAGE_KEY = "agentputer_billing";
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function defaultState(): BillingState {
  const now = new Date().toISOString();
  return {
    tierId: "free",
    credits: 0,
    cycleStart: now,
    ledger: [],
    executedProjects: [],
  };
}

/** Read and deserialize billing state, initializing defaults if not present. */
export function getState(): BillingState {
  if (typeof window === "undefined") return defaultState();

  const raw = localStorage.getItem(STORAGE_KEY);
  let state: BillingState;

  if (!raw) {
    state = defaultState();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return state;
  }

  try {
    state = JSON.parse(raw) as BillingState;
  } catch {
    state = defaultState();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return state;
  }

  // Monthly reset: if cycleStart is more than 30 days ago, grant new credits
  const cycleAge = Date.now() - new Date(state.cycleStart).getTime();
  if (cycleAge > THIRTY_DAYS_MS) {
    const tier = TIERS[state.tierId];
    const now = new Date().toISOString();
    state = {
      ...state,
      credits: state.credits + tier.creditsPerMonth,
      cycleStart: now,
      ledger: [
        ...state.ledger,
        {
          type: "monthly_grant",
          amount: tier.creditsPerMonth,
          description: `${tier.name} monthly credit renewal`,
          timestamp: now,
        },
      ],
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  return state;
}

function setState(state: BillingState): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

/** Current credit balance. */
export function getCredits(): number {
  return getState().credits;
}

/** Full Tier object for the user's current tier. */
export function getTier(): Tier {
  return TIERS[getState().tierId];
}

/**
 * Upgrade (or downgrade) to a new tier.
 * If upgrading, immediately grants the credit delta.
 */
export function changeTier(newTierId: TierId): void {
  const state = getState();
  const oldTier = TIERS[state.tierId];
  const newTier = TIERS[newTierId];
  const now = new Date().toISOString();

  const delta = Math.max(0, newTier.creditsPerMonth - oldTier.creditsPerMonth);
  const newState: BillingState = {
    ...state,
    tierId: newTierId,
    credits: state.credits + delta,
    cycleStart: now,
    ledger: [
      ...state.ledger,
      {
        type: "tier_upgrade",
        amount: delta,
        description: `Switched from ${oldTier.name} to ${newTier.name}${delta > 0 ? ` (+${delta} credits)` : ""}`,
        timestamp: now,
      },
    ],
  };
  setState(newState);
}

/**
 * Add credits from a pack purchase.
 * Throws if the user is on the Free tier — a paid subscription is required.
 */
export function purchasePack(packId: string): void {
  const pack = CREDIT_PACKS.find((p) => p.id === packId);
  if (!pack) throw new Error(`Unknown pack: ${packId}`);

  const state = getState();
  if (state.tierId === "free") throw new Error("A paid subscription is required to purchase credit packs.");

  const state = getState();
  const now = new Date().toISOString();
  setState({
    ...state,
    credits: state.credits + pack.credits,
    ledger: [
      ...state.ledger,
      {
        type: "pack_purchase",
        amount: pack.credits,
        description: `Purchased ${pack.label} for $${pack.price}`,
        timestamp: now,
      },
    ],
  });
}

/**
 * Returns true if the user can execute this project.
 * @param cost - Credit cost from estimateProjectCost().totalCredits
 */
export function canExecuteProject(projectId: string, cost: number): boolean {
  const state = getState();
  return state.credits >= cost && !state.executedProjects.includes(projectId);
}

/**
 * Deduct the estimated credit cost for a project execution.
 * Idempotent: calling again for the same projectId is a no-op.
 * Throws if insufficient credits.
 *
 * @param cost - Credit cost from estimateProjectCost().totalCredits
 */
export function deductCredit(projectId: string, cost: number): void {
  const state = getState();

  if (state.executedProjects.includes(projectId)) return; // already charged
  if (state.credits < cost) throw new Error("Insufficient credits");

  const now = new Date().toISOString();
  const newBalance = Math.round((state.credits - cost) * 100) / 100;
  setState({
    ...state,
    credits: newBalance,
    executedProjects: [...state.executedProjects, projectId],
    ledger: [
      ...state.ledger,
      {
        type: "project_execution",
        amount: -cost,
        description: `Project execution (${cost} credits)`,
        projectId,
        timestamp: now,
      },
    ],
  });
}

// ── Token-based pricing ────────────────────────────────────────────────────────

/**
 * Credits charged per 1 million tokens — matches the per-million pricing
 * structure used by LLM providers (Anthropic, OpenAI, etc.).
 *
 * Note: "CPM" technically means cost per thousand (mille), but the industry
 * quotes LLM token prices per million because it sounds better. These rates
 * are per million tokens, not per thousand.
 */
export const PRICING = {
  /** Credits per 1M input tokens. */
  inputPerMillion: 3,
  /** Credits per 1M output tokens. */
  outputPerMillion: 15,
  /**
   * Estimated tokens generated per hour of agent work.
   * Derived from typical multi-agent swarm throughput across a project lifecycle.
   */
  tokensPerHour: 75_000,
  /** Fraction of total tokens that are input (prompt) vs output (completion). */
  inputRatio: 0.70,
} as const;

export interface CostEstimate {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  inputCredits: number;
  outputCredits: number;
  /** Total credits to charge — rounded to 2 decimal places. */
  totalCredits: number;
}

/**
 * Estimate execution cost from the proposal's `estimated_hours`.
 * Uses the same CPM structure as LLM providers — cost scales with token volume,
 * not a flat fee.
 */
export function estimateProjectCost(estimatedHours: number): CostEstimate {
  const totalTokens = Math.round(estimatedHours * PRICING.tokensPerHour);
  const inputTokens = Math.round(totalTokens * PRICING.inputRatio);
  const outputTokens = totalTokens - inputTokens;

  const inputCredits = (inputTokens / 1_000_000) * PRICING.inputPerMillion;
  const outputCredits = (outputTokens / 1_000_000) * PRICING.outputPerMillion;
  const totalCredits = Math.round((inputCredits + outputCredits) * 100) / 100;

  return { inputTokens, outputTokens, totalTokens, inputCredits, outputCredits, totalCredits };
}

/** Days remaining in the current billing cycle. */
export function daysUntilRenewal(): number {
  const state = getState();
  const cycleAge = Date.now() - new Date(state.cycleStart).getTime();
  return Math.max(0, Math.ceil((THIRTY_DAYS_MS - cycleAge) / (24 * 60 * 60 * 1000)));
}
