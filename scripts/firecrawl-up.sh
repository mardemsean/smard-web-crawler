#!/usr/bin/env bash
# Bring up the official Firecrawl self-hosted stack at a pinned release.
# Firecrawl needs API + workers + Playwright + Redis + RabbitMQ + PostgreSQL (NuQ),
# so it runs from its own upstream compose file instead of ours.
#   scripts/firecrawl-up.sh [up|down|status]
set -euo pipefail

FIRECRAWL_REF="${FIRECRAWL_REF:-v2.11.597}"
SMARD_HOME="${SMARD_HOME:-$HOME/.smard-crawler}"
DIR="$SMARD_HOME/vendor/firecrawl"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-up}"

if [ -f "$REPO_DIR/.env" ]; then set -a; . "$REPO_DIR/.env"; set +a; fi
if [ -f "$SMARD_HOME/.env" ]; then set -a; . "$SMARD_HOME/.env"; set +a; fi

case "$ACTION" in
  down) docker compose -f "$DIR/docker-compose.yaml" --project-directory "$DIR" down; exit 0 ;;
  status) docker compose -f "$DIR/docker-compose.yaml" --project-directory "$DIR" ps; exit 0 ;;
  up) ;;
  *) echo "usage: $0 [up|down|status]"; exit 2 ;;
esac

if [ ! -d "$DIR/.git" ]; then
  mkdir -p "$(dirname "$DIR")"
  git clone --depth 1 --branch "$FIRECRAWL_REF" https://github.com/firecrawl/firecrawl.git "$DIR"
else
  git -C "$DIR" fetch --depth 1 origin tag "$FIRECRAWL_REF"
  git -C "$DIR" checkout -q "$FIRECRAWL_REF"
fi

# Firecrawl's compose reads only its own root .env; derive proxy settings from PROXY_URL.
python3 - "$DIR/.env" <<'PY'
import os, sys
from urllib.parse import urlsplit, unquote
env = {"USE_DB_AUTHENTICATION": "false", "PORT": "3002", "HOST": "0.0.0.0"}
proxy = os.environ.get("PROXY_URL", "")
if proxy:
    p = urlsplit(proxy)
    env["PROXY_SERVER"] = f"{p.scheme}://{p.hostname}:{p.port}" if p.port else f"{p.scheme}://{p.hostname}"
    if p.username: env["PROXY_USERNAME"] = unquote(p.username)
    if p.password: env["PROXY_PASSWORD"] = unquote(p.password)
with open(sys.argv[1], "w") as f:
    f.writelines(f"{k}={v}\n" for k, v in env.items())
os.chmod(sys.argv[1], 0o600)
PY

docker compose -f "$DIR/docker-compose.yaml" --project-directory "$DIR" up -d --build
echo "Firecrawl $FIRECRAWL_REF starting on http://localhost:3002 (first build takes several minutes)."
echo "Set FIRECRAWL_HOST=http://localhost:3002 in .env (already the default)."
