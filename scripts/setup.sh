#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Environment Setup Script for smard-web-crawler
# Paste into: Environment settings → Setup script
# Clones component source repos so the agent has local reference without
# spending tokens on discovery. Installs all Python deps from source.
# ==============================================================================

echo "=== smard-web-crawler: Environment Setup ==="

# --- System dependencies ---
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  curl wget git jq unzip \
  libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
  libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
  libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
  libcairo2 libasound2t64 libatspi2.0-0 2>/dev/null || true

# ==============================================================================
# Clone component source repositories (shallow, read-only reference)
# These give the agent direct access to source code, docs, examples and
# docker configs without burning tokens on web search or pip introspection.
# ==============================================================================

VENDOR_DIR="/home/user/vendor"
mkdir -p "$VENDOR_DIR"

echo "--- Cloning Crawl4AI source ---"
if [ ! -d "$VENDOR_DIR/crawl4ai" ]; then
  git clone --depth 1 https://github.com/unclecode/crawl4ai.git "$VENDOR_DIR/crawl4ai" || true
fi

echo "--- Cloning Firecrawl source (self-hosted) ---"
if [ ! -d "$VENDOR_DIR/firecrawl" ]; then
  git clone --depth 1 https://github.com/mendableai/firecrawl.git "$VENDOR_DIR/firecrawl" || true
fi

echo "--- Cloning playwright-stealth ---"
if [ ! -d "$VENDOR_DIR/playwright-stealth" ]; then
  git clone --depth 1 https://github.com/AtuboDad/playwright_stealth.git "$VENDOR_DIR/playwright-stealth" || true
fi

echo "--- Cloning Playwright (Python) ---"
if [ ! -d "$VENDOR_DIR/playwright-python" ]; then
  git clone --depth 1 https://github.com/microsoft/playwright-python.git "$VENDOR_DIR/playwright-python" || true
fi

# ==============================================================================
# Install Python dependencies
# ==============================================================================

echo "--- Installing Python packages ---"
pip3 install --quiet --no-cache-dir \
  crawl4ai \
  firecrawl-py \
  playwright \
  httpx \
  beautifulsoup4 \
  markdownify \
  pydantic \
  rich \
  tenacity \
  python-dotenv \
  aiofiles

# Stealth: try PyPI first, fall back to cloned source
pip3 install --quiet --no-cache-dir playwright-stealth 2>/dev/null || \
  pip3 install --quiet --no-cache-dir "$VENDOR_DIR/playwright-stealth" 2>/dev/null || true

# Crawl4AI post-install setup
python3 -c "from crawl4ai import setup; setup()" 2>/dev/null || \
  crawl4ai-setup 2>/dev/null || true

# ==============================================================================
# Playwright browsers
# ==============================================================================

if [ -d "/opt/pw-browsers" ]; then
  echo "Playwright browsers found at /opt/pw-browsers"
  export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
  export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
else
  echo "Installing Playwright Chromium..."
  python3 -m playwright install chromium --with-deps 2>/dev/null || true
fi

# ==============================================================================
# Project setup
# ==============================================================================

PROJECT_DIR="/home/user/smard-web-crawler"
if [ -d "$PROJECT_DIR" ]; then
  mkdir -p "$PROJECT_DIR/data/output"
  cd "$PROJECT_DIR"
  if [ ! -f .env ]; then
    cp -n .env.example .env 2>/dev/null || true
  fi
fi

# ==============================================================================
# Summary for the agent
# ==============================================================================

cat <<'SUMMARY'
=== Setup complete ===

Vendor sources (read-only reference):
  /home/user/vendor/crawl4ai          — Crawl4AI source, docs, examples
  /home/user/vendor/firecrawl         — Firecrawl source, docker configs, API docs
  /home/user/vendor/playwright-stealth — playwright-stealth patches
  /home/user/vendor/playwright-python  — Playwright Python bindings source

Key paths:
  Firecrawl docker-compose: /home/user/vendor/firecrawl/docker-compose.yaml
  Crawl4AI examples:        /home/user/vendor/crawl4ai/docs/
  Firecrawl .env template:  /home/user/vendor/firecrawl/apps/api/.env.example

Services:
  docker compose up -d       — start Firecrawl + Crawl4AI containers
  python3 scripts/demo.py    — test unified scraper

Env vars to configure (in environment secrets):
  PROXY_URL                  — residential proxy (e.g. http://user:pass@host:port)
SUMMARY
