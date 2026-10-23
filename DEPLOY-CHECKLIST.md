## Deploy Checklist: smard-web-crawler
**Date:** 2026-10-21 | **Deployer:** Prof. Sean Mardem

### Pre-Deploy
- [ ] Installer ran: `scripts/install.sh` (or `scripts\install.ps1`); `smard-crawler --help` works
- [ ] `~/.smard-crawler/.env` has real credentials (PROXY_URL, SITE_UNBLOCKER_URL, DECODO_API_KEY) and generated tokens (OBSCURA_CDP_TOKEN, CRAWL4AI_API_TOKEN, SMARD_API_TOKEN)
- [ ] Tests pass: `pytest -q` and `OBSCURA_BIN=~/.smard-crawler/bin/obscura pytest -q`
- [ ] Docker services healthy: `docker compose --env-file ~/.smard-crawler/.env up -d && docker compose ps`
- [ ] Crawl4AI reachable: `curl -s http://127.0.0.1:11235/health`
- [ ] Obscura reachable: `curl -s -H "Authorization: Bearer $OBSCURA_CDP_TOKEN" http://127.0.0.1:9222/json/version`
- [ ] Firecrawl (optional): `scripts/firecrawl-up.sh` then `curl -s http://127.0.0.1:3002/`
- [ ] `smard-crawler health` lists the expected engines as up
- [ ] Rollback plan: `git revert HEAD` or `docker compose down && docker compose up -d` with previous image tags

### Infrastructure Verification
- [ ] Residential proxy functional: `curl -x $PROXY_URL https://httpbin.org/ip`
- [ ] Decodo Site Unblocker functional: `curl -x $SITE_UNBLOCKER_URL https://httpbin.org/ip` (verify different IP)
- [ ] Decodo Web Data API key valid: `curl -H "Authorization: Bearer $DECODO_API_KEY" https://data.decodo.com/v1/scrape -d '{"url":"https://example.com"}'`
- [ ] DNS resolution working for all proxy endpoints
- [ ] Outbound HTTPS (443) open to target domains

### Stealth Verification
- [ ] Engine battery on the production host: `smard-crawler bench --engines obscura-stealth,cloakbrowser,chromium --rounds 5 --online`
- [ ] Obscura `ja4` equals real Chrome's; sannysoft failures <= 3
- [ ] OBSCURA_TIMEZONE / OBSCURA_GEOLOCATION match the proxy exit region

### Smoke Test (all three fallback levels)
- [ ] Level 1 — Self-hosted engine scrape: `smard-crawler scrape https://example.com --engine obscura`
- [ ] Level 2 — Force Site Unblocker fallback: temporarily disable Crawl4AI, verify Site Unblocker activates
- [ ] Level 3 — Force Web Data API fallback: disable both Crawl4AI and Site Unblocker, verify API fallback
- [ ] Batch scrape with 5+ URLs: verify concurrency and output markdown files in data/output/
- [ ] Markdown output includes YAML frontmatter with url, timestamp, engine metadata

### Resilience Pattern Verification
- [ ] Intra-engine retry: trigger a temporary failure (e.g., network timeout) and confirm retry with variant params before engine escalation
- [ ] Liveness check: after LIVENESS_INTERVAL (300s), verify health recheck fires
- [ ] Pool cascade recheck: during batch, confirm _recheck_failed_engines runs at BATCH_RECHECK_INTERVAL (10 completed)

### Post-Deploy
- [ ] Confirm all three fallback levels produce valid markdown
- [ ] Monitor proxy credit/bandwidth usage (Decodo dashboard)
- [ ] Verify no credential leaks in output files or logs
- [ ] Update RESEARCH/Exploration.md with production deployment status if applicable

### Rollback Triggers
- Crawl4AI or Firecrawl container crash loops (>3 restarts in 5 min)
- Proxy authentication failures on >50% of requests
- Decodo API returns 429 (rate limited) persistently
- Output markdown is empty or malformed for >3 consecutive URLs
- Memory usage exceeds 4GB per container

### Blockers status (2026-10-23)
- Test suite: **resolved**. 192 tests, including real-Obscura integration and HTTP-level client tests.
- stealth.py: **resolved**. Upgraded and benchmarked. Obscura and CloakBrowser carry their own stealth (see docs/decisions/0001-obscura-engine.md).
- CI/CD: **resolved**. `.github/workflows/ci.yml` covers unit, integration, bench smoke and compose validation.
- Rate limiting: **resolved**. PaidGuard enforces `DECODO_MAX_RPS` and `DECODO_DAILY_LIMIT`, and health checks never spend billed requests.
- Monitoring/alerting: **open**. `smard-crawler health` and `/health` expose state and today's paid budget; external alerting is not set up.

### Recommendation
Ready for staging on SMardSERVER. Before production: run the battery with
`--online` on direct egress, run the three-level smoke test with real Decodo
credentials, and wire `/health` into the operator's monitoring.
