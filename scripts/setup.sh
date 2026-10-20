#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Environment Setup Script for Web Scraper Toolkit
# Add this to your Claude Code cloud environment's Setup Script field
# ==============================================================================

echo "=== Web Scraper Toolkit: Environment Setup ==="

# --- System dependencies ---
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  curl wget git jq unzip \
  libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
  libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
  libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
  libcairo2 libasound2t64 libatspi2.0-0 2>/dev/null || true

# --- Python packages ---
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

# --- Playwright stealth plugin ---
pip3 install --quiet --no-cache-dir playwright-stealth 2>/dev/null || \
  pip3 install --quiet --no-cache-dir git+https://github.com/AmeenAli/playwright_stealth.git 2>/dev/null || true

# --- Crawl4AI post-install setup ---
python3 -c "from crawl4ai import setup; setup()" 2>/dev/null || \
  crawl4ai-setup 2>/dev/null || true

# --- Verify Playwright browsers ---
if [ -d "/opt/pw-browsers" ]; then
  echo "Playwright browsers found at /opt/pw-browsers"
  export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
  export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
else
  echo "Installing Playwright Chromium..."
  python3 -m playwright install chromium --with-deps 2>/dev/null || true
fi

# --- Create working directories ---
mkdir -p /home/user/web-scraper-toolkit/data/output

# --- Copy .env if not exists ---
cd /home/user/web-scraper-toolkit
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || true
  echo "Created .env from template - fill in your proxy credentials"
fi

echo "=== Setup complete ==="
echo "Services available:"
echo "  Firecrawl: docker compose up firecrawl-api"
echo "  Crawl4AI:  docker compose up crawl4ai"
echo "  Both:      docker compose up -d"
