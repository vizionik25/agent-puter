# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile.backend — Multi-stage build using the official uv pattern.
# Reference: https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile
#
# Stage 1 (builder): ghcr.io/astral-sh/uv:python3.14-bookworm-slim
#   - uv is pre-installed in this image; no separate pip install step needed.
#   - Deps-only sync first (--no-install-project) for better layer caching.
#   - Full sync second (copies project source into the venv).
#
# Stage 2 (runtime): python:3.14-slim-bookworm
#   - Must match the builder image's Python version exactly (same interpreter path).
#   - uv is NOT present; only the pre-built /app/.venv is copied across.
#   - Runs as a non-root user.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

# Compile .pyc files so the runtime image starts faster.
# copy mode: venv files are copied (not symlinked) so they work after the
# /root/.cache/uv bind-mount is removed in the final image.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# ── Step 1: install dependencies only (not the project itself).
# Using bind-mounts for the lock file and pyproject.toml means these files
# don't add a layer, so the cache is busted ONLY when they change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# ── Step 2: copy source then install the project itself into the venv.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
# Must use the SAME Python version as the builder image so the interpreter
# path (/usr/local/bin/python3.14) is identical inside /app/.venv.
FROM python:3.14-slim-bookworm AS runtime

# Non-root user for security
RUN groupadd --system --gid 999 app \
 && useradd  --system --gid 999 --uid 999 --create-home app

# Copy the entire /app directory (venv + source) from the builder.
# Only the venv is strictly required at runtime; source is included so
# PYTHONPATH resolution via the editable install continues to work.
COPY --from=builder --chown=app:app /app /app

# Put the venv's executables first on PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# ── Runtime configuration (override via .env or docker compose env_file) ─────
# LLM / Puter
ENV PUTER_MODEL="" \
    PUTER_AUTH_TOKEN="" \
    PUTER_API_BASE=""

# Stripe
ENV STRIPE_SECRET_KEY="" \
    STRIPE_PUBLISHABLE_KEY="" \
    STRIPE_WEBHOOK_SECRET=""

WORKDIR /app
USER app

EXPOSE 9999

CMD ["python", "-m", "uvicorn", "agent_puter.swarm.main:app", \
     "--host", "0.0.0.0", "--port", "9999", "--proxy-headers"]
