<div align="center">

<img width="80" src="https://em-content.zobj.net/source/apple/391/high-voltage_26a1.png" alt="logo" />

# Agent-Puter — Frontend

**Client portal for the Agent-Puter AI consulting agency**

*Next.js 16 · Stripe payments · Tailwind CSS · Dark glassmorphism UI*

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet?style=flat-square)](../LICENSE)

</div>

---

## What is this?

This is the client-facing Next.js portal for [agent-puter](https://github.com/vizionik25/agent-puter) — a fully autonomous AI consulting agency backend. The frontend provides:

- **`/`** — Landing page
- **`/consult`** — Live AI consultation chat (Sales Agent)
- **`/proposal/[id]`** — Proposal viewer
- **`/pay/[id]/deposit`** — Stripe 20 % deposit
- **`/pay/[id]/final`** — Stripe 80 % balance
- **`/demo/[id]`** — Gated demo viewer
- **`/status/[id]`** — Real-time progress tracker (auto-refresh)

It communicates with the Python backend over a simple REST/JSON API. All `/api/*` requests are proxied through Next.js to avoid CORS issues in development.

---

## Prerequisites

- Node.js ≥ 20 and npm (use [nvm](https://github.com/nvm-sh/nvm))
- A running **agent-puter backend** (see [Connecting to the backend](#connecting-to-the-backend))
- A [Stripe](https://stripe.com) account (test keys work fine)

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/vizionik25/agent-puter-frontend.git
cd agent-puter-frontend
```

> Or, if you cloned the full monorepo:
> ```bash
> cd agent-puter/frontend
> ```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment

Create a `.env.local` file in this directory:

```env
# Point at your running backend (default: local dev)
NEXT_PUBLIC_API_URL=http://localhost:9999

# Stripe publishable key (test or live)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

> [!IMPORTANT]
> `NEXT_PUBLIC_API_URL` is embedded at **build time**. Set it before running
> `npm run build` or building the Docker image.

### 4. Start the dev server

```bash
npm run dev
# → http://localhost:3000
```

---

## Connecting to the Backend

The frontend is a pure REST client — it doesn't care how the backend is running,
only that `NEXT_PUBLIC_API_URL` points at it.

### Option A — Backend from PyPI (recommended for non-developers)

```bash
# Install the agent-puter CLI globally
uv tool install agent-puter

# Create a .env file with your credentials (see main repo README)
# then run:
agent-puter
# → http://localhost:9999
```

### Option B — Backend cloned from source

```bash
git clone https://github.com/vizionik25/agent-puter.git
cd agent-puter
cp .env.example .env   # fill in PUTER_AUTH_TOKEN, STRIPE keys, etc.
uv sync
uv run agent-puter
# → http://localhost:9999
```

### Option C — Remote/hosted backend

Set `NEXT_PUBLIC_API_URL` to your public backend URL:

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## Docker

Run the frontend in a container (backend must be reachable at `NEXT_PUBLIC_API_URL`):

```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... \
docker compose up --build -d
# → http://localhost:3000
```

> [!IMPORTANT]
> Pass `NEXT_PUBLIC_API_URL` as a shell variable **before** the `docker compose`
> command — Next.js bakes it into the bundle at image build time.

---

## Deploy to Vercel

The fastest way to deploy is [Vercel](https://vercel.com/new):

1. Import `https://github.com/vizionik25/agent-puter-frontend` into Vercel.
2. Set these environment variables in the Vercel project settings:
   - `NEXT_PUBLIC_API_URL` — your backend URL
   - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` — your Stripe live publishable key
3. Deploy — Vercel handles the build and CDN.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx           Root layout + nav
│   ├── globals.css          Design system (dark navy + violet)
│   ├── page.tsx             Landing page
│   ├── consult/page.tsx     AI consultation chat
│   ├── proposal/[id]/       Proposal viewer
│   ├── pay/[id]/deposit/    Stripe 20% deposit
│   ├── pay/[id]/final/      Stripe 80% balance
│   ├── demo/[id]/           Demo viewer (gated)
│   └── status/[id]/         Live progress tracker
├── lib/
│   └── api.ts               Typed REST API client
├── next.config.ts           API proxy → NEXT_PUBLIC_API_URL
├── Dockerfile               Standalone Next.js image
├── docker-compose.yml       Frontend-only compose
└── .env.local               ← create this (not committed)
```

---

## License

MIT © 2026 Charles Nichols — [vizionikmedia.com](https://vizionikmedia.com)
