#!/usr/bin/env bash
# SMard Web Crawler installer for Linux and macOS.
#
#   scripts/install.sh [--prefix DIR] [--with-cloak] [--with-docker] [--with-firecrawl]
#                      [--with-chromium] [--no-obscura] [--dev]
#
# Installs into ~/.smard-crawler (venv, Obscura stealth binary, .env with generated
# tokens) and links `smard-crawler` and `smard-crawler-mcp` into ~/.local/bin.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${SMARD_HOME:-$HOME/.smard-crawler}"
BIN_LINK_DIR="${SMARD_BIN_DIR:-$HOME/.local/bin}"
OBSCURA_VERSION="v0.2.5"
WITH_CLOAK=0 WITH_DOCKER=0 WITH_FIRECRAWL=0 WITH_CHROMIUM=0 WITH_OBSCURA=1 DEV=0

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift ;;
    --with-cloak) WITH_CLOAK=1 ;;
    --with-docker) WITH_DOCKER=1 ;;
    --with-firecrawl) WITH_FIRECRAWL=1 ;;
    --with-chromium) WITH_CHROMIUM=1 ;;
    --no-obscura) WITH_OBSCURA=0 ;;
    --dev) DEV=1 ;;
    -h|--help) sed -n 2,9p "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# --- Python >= 3.12 -----------------------------------------------------------
PY=""
for cand in python3.13 python3.12 python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    PY="$(command -v "$cand")"; break
  fi
done
[ -n "$PY" ] || die "Python 3.12+ is required (found: $(python3 --version 2>&1 || echo none))"
say "Python: $("$PY" --version) at $PY"

mkdir -p "$PREFIX/bin" "$PREFIX/output"
chmod 700 "$PREFIX"

# --- Virtualenv + package -----------------------------------------------------
if [ ! -x "$PREFIX/venv/bin/python" ]; then
  say "Creating virtualenv in $PREFIX/venv"
  "$PY" -m venv "$PREFIX/venv"
fi
VPY="$PREFIX/venv/bin/python"
"$VPY" -m pip install --quiet --upgrade pip
EXTRAS="server,mcp,bench"
[ "$WITH_CLOAK" = 1 ] && EXTRAS="$EXTRAS,cloak"
[ "$DEV" = 1 ] && EXTRAS="$EXTRAS,dev"
# Pinned versions for a reproducible install; skipped if the file is absent.
CONSTRAINTS=""
[ -f "$REPO_DIR/constraints.txt" ] && CONSTRAINTS="-c $REPO_DIR/constraints.txt"
say "Installing smard-web-crawler[$EXTRAS]"
if [ "$DEV" = 1 ]; then
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 "$VPY" -m pip install --quiet $CONSTRAINTS -e "$REPO_DIR[$EXTRAS]"
else
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 "$VPY" -m pip install --quiet $CONSTRAINTS "$REPO_DIR[$EXTRAS]"
fi
if [ "$WITH_CHROMIUM" = 1 ]; then
  say "Installing Playwright Chromium (baseline engine for the benchmark)"
  "$VPY" -m playwright install chromium
fi

# --- Obscura stealth binary ---------------------------------------------------
OBSCURA_BIN=""
if [ "$WITH_OBSCURA" = 1 ]; then
  os="$(uname -s)"; arch="$(uname -m)"
  case "$os/$arch" in
    Linux/x86_64)            asset=obscura-x86_64-linux-stealth.tar.gz  sum=d9175cf7573d0243fc303a6f1a3b68affc757af0b5549cacb018e9670988316c ;;
    Linux/aarch64|Linux/arm64) asset=obscura-aarch64-linux-stealth.tar.gz sum=e28ed5ff2dbabe8d820c7b1ef56e6005399aff15912c7774777719e66a021a32 ;;
    Darwin/arm64)            asset=obscura-aarch64-macos-stealth.tar.gz sum=9baab9b1d2e0862adb70ce2c81903b5a799bee026038130b9141fab597874100 ;;
    Darwin/x86_64)           asset=obscura-x86_64-macos-stealth.tar.gz  sum=95ace7af8bb3eecbaa6c64b4869be2eaf421b8ced0a25c3b9981e18f8e681de6 ;;
    *) die "no Obscura build for $os/$arch (rerun with --no-obscura)" ;;
  esac
  if [ ! -x "$PREFIX/bin/obscura" ] || ! "$PREFIX/bin/obscura" --version 2>/dev/null | grep -q "${OBSCURA_VERSION#v}"; then
    say "Downloading Obscura $OBSCURA_VERSION ($asset)"
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/obscura.tgz" "https://github.com/h4ckf0r0day/obscura/releases/download/$OBSCURA_VERSION/$asset"
    got="$( (sha256sum "$tmp/obscura.tgz" 2>/dev/null || shasum -a 256 "$tmp/obscura.tgz") | awk '{print $1}')"
    [ "$got" = "$sum" ] || die "Obscura checksum mismatch: expected $sum, got $got"
    tar xzf "$tmp/obscura.tgz" -C "$PREFIX/bin"
    rm -rf "$tmp"
    chmod +x "$PREFIX/bin/obscura" "$PREFIX/bin/obscura-worker"
  fi
  OBSCURA_BIN="$PREFIX/bin/obscura"
  say "Obscura: $("$OBSCURA_BIN" --version)"
fi

# --- .env with generated secrets ---------------------------------------------
ENV_FILE="$PREFIX/.env"
if [ ! -f "$ENV_FILE" ]; then
  say "Writing $ENV_FILE (tokens generated; add proxy/Decodo credentials yourself)"
  cp "$REPO_DIR/.env.example" "$ENV_FILE"
fi
"$VPY" - "$ENV_FILE" "$OBSCURA_BIN" "$PREFIX/output" "$WITH_CLOAK" <<'PY'
import re, secrets, sys
path, obscura_bin, output_dir, with_cloak = sys.argv[1:5]
text = open(path).read()

def setdefault(key, value, force=False):
    global text
    pat = re.compile(rf"^{key}=(.*)$", re.M)
    m = pat.search(text)
    if m is None:
        text += f"\n{key}={value}\n"
    elif force or not m.group(1).strip():
        text = pat.sub(f"{key}={value}", text, count=1)

setdefault("OBSCURA_CDP_TOKEN", secrets.token_hex(32))
setdefault("SMARD_API_TOKEN", secrets.token_hex(32))
setdefault("CRAWL4AI_API_TOKEN", secrets.token_hex(32))
setdefault("OBSCURA_CDP_URL", "ws://127.0.0.1:9222")
if obscura_bin:
    setdefault("OBSCURA_BIN", obscura_bin, force=True)
setdefault("OUTPUT_DIR", output_dir, force=output_dir and "./data/output" in text)
if with_cloak == "1":
    setdefault("CLOAKBROWSER_ENABLED", "true", force=True)
open(path, "w").write(text)
PY
chmod 600 "$ENV_FILE"

# --- Command links ------------------------------------------------------------
mkdir -p "$BIN_LINK_DIR"
for cmd in smard-crawler smard-crawler-mcp; do
  ln -sf "$PREFIX/venv/bin/$cmd" "$BIN_LINK_DIR/$cmd"
done
case ":$PATH:" in
  *":$BIN_LINK_DIR:"*) ;;
  *) say "Add $BIN_LINK_DIR to PATH:  echo 'export PATH=\"$BIN_LINK_DIR:\$PATH\"' >> ~/.profile" ;;
esac

# --- Optional services --------------------------------------------------------
if [ "$WITH_DOCKER" = 1 ]; then
  command -v docker >/dev/null || die "docker not found"
  say "Starting Docker services (obscura, crawl4ai, api)"
  docker compose --project-directory "$REPO_DIR" --env-file "$ENV_FILE" up -d --build
fi
if [ "$WITH_FIRECRAWL" = 1 ]; then
  SMARD_HOME="$PREFIX" "$REPO_DIR/scripts/firecrawl-up.sh" up
fi

# --- Verify -------------------------------------------------------------------
say "Engine health:"
SMARD_HOME="$PREFIX" "$PREFIX/venv/bin/smard-crawler" health || true

cat <<EOF

Installed.
  CLI:        smard-crawler scrape https://example.com
  HTTP API:   smard-crawler serve            (http://127.0.0.1:8787, Bearer \$SMARD_API_TOKEN)
  MCP:        claude mcp add --scope user smard-crawler -- $PREFIX/venv/bin/smard-crawler-mcp
  Plugin:     /plugin marketplace add mardemsean/smard-web-crawler
              /plugin install smard-crawler@smard-labs
  Config:     $ENV_FILE
EOF
