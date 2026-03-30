# syntax=docker/dockerfile:1
#
# Build with BuildKit (default in Docker Desktop) so RUN --mount=type=cache reuses:
#   - apt lists/packages, pip wheels, npm tarballs, Playwright browser downloads
# Use: docker compose build   (or DOCKER_BUILDKIT=1 docker build ...)
#
FROM node:24-bookworm AS base

LABEL vendor=neon.ai \
    ai.neon.name="CCAI-Demo"

ENV OVOS_CONFIG_BASE_FOLDER=neon
ENV OVOS_CONFIG_FILENAME=neon.yaml
ENV XDG_CONFIG_HOME=/config
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV NPM_CONFIG_PREFER_OFFLINE=true

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (layer invalidates only when requirements change) --
WORKDIR /ccai/multi_llm_chatbot_backend
COPY multi_llm_chatbot_backend/requirements/requirements.txt requirements/
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-wheels \
    pip install --break-system-packages -r requirements/requirements.txt

# ---- Node dependencies (layer invalidates only when package files change) ---
WORKDIR /ccai/phd-advisor-frontend
COPY phd-advisor-frontend/package.json phd-advisor-frontend/package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm,id=npm-cache \
    npm install --prefer-offline --no-audit --no-fund

# ---- Copy the rest of the source code (this layer changes often) -----------
WORKDIR /ccai
COPY . .

# ---- Backend target --------------------------------------------------------
FROM base AS backend
WORKDIR /ccai/multi_llm_chatbot_backend
# Persist Chromium downloads across rebuilds (otherwise ~300MB+ each build)
RUN --mount=type=cache,target=/root/.cache/ms-playwright,id=playwright-browsers \
    python3 -m playwright install --with-deps chromium
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Frontend target -------------------------------------------------------
FROM base AS frontend
WORKDIR /ccai/phd-advisor-frontend
CMD [ "npm", "start" ]
