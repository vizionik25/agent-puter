# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — dependency installer
#   Installs node_modules in isolation so the layer is cached between builds.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-slim AS deps

WORKDIR /app

# Copy manifests only — bust cache only when deps change
COPY package.json package-lock.json ./

RUN npm ci --omit=dev


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — builder
#   Runs next build to produce the optimised .next/standalone output.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-slim AS builder

WORKDIR /app

# Copy deps from previous stage
COPY --from=deps /app/node_modules ./node_modules

# Copy full frontend source
COPY . ./

# Build args — injected at build time so Next.js can embed them
ARG NEXT_PUBLIC_API_URL=http://localhost:9999
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=""

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY} \
    NEXT_TELEMETRY_DISABLED=1

# Produce optimised standalone build
RUN npm run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — runtime image
#   Uses the minimal standalone Next.js server — no node_modules needed.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-slim AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root user
RUN addgroup --system nextjs && adduser --system --ingroup nextjs nextjs

# Copy only the standalone bundle and static assets
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
