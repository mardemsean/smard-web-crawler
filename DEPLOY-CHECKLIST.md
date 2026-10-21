## Deploy Checklist: smard-web-crawler
**Date:** 2026-10-21 | **Deployer:** Prof. Sean Mardem

### Pre-Deploy
- [ ] All Python imports pass: `python3 -c "from src.common.scraper import UnifiedScraper; from src.common.config import AppConfig; print('OK')"`
- [ ] `.env` file created from `.env.example` with real credentials (PROXY_URL, SITE_UNBLOCKER_URL, DECODO_API_KEY)
- [ ] Docker Compose services healthy: `docker compose up -d && docker compose ps`
- [ ] Crawl4AI reachable: `curl -s http://localhost:11235/health`
- [ ] Firecrawl reachable: `curl -s http://localhost:3002/v1/scrape -H "Authorization: Bearer test"`
- [ ] No known critical bugs in current code (0 tests exist — risk accepted or mitigated by manual smoke test)
- [ ] Rollback plan: `git revert HEAD` or `docker compose down && docker compose up -d` with previous image tags
- [ ] Python 3.12+ available: `python3 --version`
- [ ] Dependencies installed: `pip install httpx tenacity pydantic playwright`
- [ ] Playwright browsers installed: `playwright install chromium`

### Infrastructure Verification
- [ ] Residential proxy functional: `curl -x $PROXY_URL https://httpbin.org/ip`
- [ ] Decodo Site Unblocker functional: `curl -x $SITE_UNBLOCKER_URL https://httpbin.org/ip` (verify different IP)
- [ ] Decodo Web Data API key valid: `curl -H "Authorization: Bearer $DECODO_API_KEY" https://data.decodo.com/v1/scrape -d '{"url":"https://example.com"}'`
- [ ] DNS resolution working for all proxy endpoints
- [ ] Outbound HTTPS (443) open to target domains

### Stealth Verification
- [ ] stealth.py random_user_agent() returns valid Chrome UAs: `python3 -c "from src.common.stealth import random_user_agent; print(random_user_agent())"`
- [ ] stealth_headers() includes Accept, Accept-Language, Accept-Encoding
- [ ] Browser fingerprint check: navigate to https://bot.sannysoft.com with Playwright stealth and screenshot

### Smoke Test (all three fallback levels)
- [ ] Level 1 — Self-hosted engine scrape: `python3 scripts/demo.py https://example.com`
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

### Not Yet Deployable (Blockers for Production)
- **No test suite**: 0 tests exist. Cannot gate deployment on test pass.
- **stealth.py incomplete**: Current stealth is basic (5 random UAs). Obscura pattern extraction and CloakBrowser RE integration pending.
- **No CI/CD pipeline**: No GitHub Actions, no automated build/test/deploy.
- **No monitoring/alerting**: No error rate tracking, no latency monitoring, no cost alerting for Decodo API usage.
- **No rate limiting**: No internal rate limiter to prevent burning through Decodo credits.

### Recommendation
This project is at **development/staging readiness**, not production readiness. Deploy to a development environment for integration testing. Production deployment requires: test suite (>80% coverage on scraper.py), stealth.py upgrade, CI pipeline, and monitoring.
