"""Shared configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _env(name: str, default: str = "") -> str:
    """os.getenv that treats an empty value (e.g. `KEY=` in .env) as unset."""
    return os.environ.get(name) or default


SMARD_HOME = Path(_env("SMARD_HOME", str(Path.home() / ".smard-crawler")))


def load_env_files() -> list[Path]:
    """Load SMARD_ENV_FILE, then ./.env, then ~/.smard-crawler/.env; earlier files win, real env vars win over all."""
    candidates = [_env("SMARD_ENV_FILE"), Path.cwd() / ".env", SMARD_HOME / ".env"]
    loaded = []
    for c in candidates:
        if c and Path(c).is_file():
            load_dotenv(c, override=False)
            loaded.append(Path(c))
    return loaded


load_env_files()


@dataclass
class ProxyConfig:
    url: str = _env("PROXY_URL", "")
    rotation_url: str = _env("PROXY_ROTATION_URL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.url)


@dataclass
class SiteUnblockerConfig:
    url: str = _env("SITE_UNBLOCKER_URL", "")
    fallback_enabled: bool = _env("SITE_UNBLOCKER_FALLBACK", "true").lower() == "true"

    @property
    def enabled(self) -> bool:
        return bool(self.url) and self.fallback_enabled


@dataclass
class DecodoApiConfig:
    api_key: str = _env("DECODO_API_KEY", "")
    api_url: str = _env("DECODO_API_URL", "https://data.decodo.com/v1")
    fallback_enabled: bool = _env("DECODO_API_FALLBACK", "true").lower() == "true"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and self.fallback_enabled


@dataclass
class BrowserConfig:
    headless: bool = _env("BROWSER_HEADLESS", "true").lower() == "true"
    viewport_width: int = int(_env("BROWSER_VIEWPORT_WIDTH", "1920"))
    viewport_height: int = int(_env("BROWSER_VIEWPORT_HEIGHT", "1080"))
    timeout: int = int(_env("BROWSER_TIMEOUT", "30000"))
    user_agents: str = _env("BROWSER_USER_AGENTS", "auto")


@dataclass
class StealthConfig:
    enabled: bool = _env("STEALTH_ENABLED", "true").lower() == "true"
    human_simulation: bool = _env("HUMAN_SIMULATION", "true").lower() == "true"
    delay_min: int = 1000
    delay_max: int = 3000
    max_retries: int = int(_env("MAX_RETRIES_ON_BLOCK", "3"))

    def __post_init__(self):
        delay_range = _env("REQUEST_DELAY_RANGE", "1000,3000")
        parts = delay_range.split(",")
        self.delay_min = int(parts[0])
        self.delay_max = int(parts[1]) if len(parts) > 1 else self.delay_min * 3


def _env_bool(name: str, default: str) -> bool:
    return _env(name, default).lower() == "true"


@dataclass
class ObscuraConfig:
    cdp_url: str = field(default_factory=lambda: _env("OBSCURA_CDP_URL", "ws://localhost:9222"))
    token: str = field(default_factory=lambda: _env("OBSCURA_CDP_TOKEN", ""))
    enabled: bool = field(default_factory=lambda: _env_bool("OBSCURA_ENABLED", "true"))
    max_sessions: int = field(default_factory=lambda: int(_env("OBSCURA_MAX_SESSIONS", "8")))
    binary: str = field(default_factory=lambda: _env("OBSCURA_BIN", ""))


@dataclass
class CloakBrowserConfig:
    enabled: bool = field(default_factory=lambda: _env_bool("CLOAKBROWSER_ENABLED", "false"))
    max_sessions: int = field(default_factory=lambda: int(_env("CLOAKBROWSER_MAX_SESSIONS", "1")))
    humanize: bool = field(default_factory=lambda: _env_bool("CLOAKBROWSER_HUMANIZE", "false"))


@dataclass
class BudgetConfig:
    """Guards for paid Decodo engines (Site Unblocker, Web Data API)."""

    max_rps: float = field(default_factory=lambda: float(_env("DECODO_MAX_RPS", "2")))
    daily_limit: int = field(default_factory=lambda: int(_env("DECODO_DAILY_LIMIT", "1000")))
    state_file: Path = field(default_factory=lambda: Path(_env("BUDGET_STATE_FILE", str(SMARD_HOME / "budget.json"))))


DEFAULT_ENGINE_ORDER = "obscura,crawl4ai,firecrawl,cloakbrowser,site_unblocker,web_data_api"


@dataclass
class OutputConfig:
    dir: Path = field(default_factory=lambda: Path(_env("OUTPUT_DIR", "./data/output")))
    format: str = _env("OUTPUT_FORMAT", "markdown")
    include_meta: bool = _env("OUTPUT_INCLUDE_META", "true").lower() == "true"


@dataclass
class AppConfig:
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    site_unblocker: SiteUnblockerConfig = field(default_factory=SiteUnblockerConfig)
    decodo_api: DecodoApiConfig = field(default_factory=DecodoApiConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    obscura: ObscuraConfig = field(default_factory=ObscuraConfig)
    cloakbrowser: CloakBrowserConfig = field(default_factory=CloakBrowserConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    engine_order: list[str] = field(default_factory=lambda: [
        e.strip() for e in _env("ENGINE_ORDER", DEFAULT_ENGINE_ORDER).split(",") if e.strip()
    ])
    respect_robots: bool = field(default_factory=lambda: _env_bool("RESPECT_ROBOTS", "true"))
    robots_user_agent: str = field(default_factory=lambda: _env("ROBOTS_USER_AGENT", "SMardCrawler"))

    firecrawl_host: str = _env("FIRECRAWL_HOST", "http://localhost:3002")
    firecrawl_api_key: str = _env("FIRECRAWL_API_KEY", "fc-local-dev")
    crawl4ai_base_url: str = _env("CRAWL4AI_BASE_URL", "http://localhost:11235")
    crawl4ai_strategy: str = _env("CRAWL4AI_DEFAULT_STRATEGY", "pruning")

    log_level: str = _env("LOG_LEVEL", "INFO")
    log_file: str = _env("LOG_FILE", "./data/scraper.log")

    @property
    def site_unblocker_url(self) -> str:
        return self.site_unblocker.url

    @property
    def decodo_api_key(self) -> str:
        return self.decodo_api.api_key

    @property
    def decodo_api_url(self) -> str:
        return self.decodo_api.api_url


config = AppConfig()
