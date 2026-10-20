"""Shared configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProxyConfig:
    url: str = os.getenv("PROXY_URL", "")
    rotation_url: str = os.getenv("PROXY_ROTATION_URL", "")
    api_key: str = os.getenv("PROXY_API_KEY", "")

    @property
    def enabled(self) -> bool:
        return bool(self.url)


@dataclass
class BrowserConfig:
    headless: bool = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    viewport_width: int = int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1920"))
    viewport_height: int = int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "1080"))
    timeout: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    user_agents: str = os.getenv("BROWSER_USER_AGENTS", "auto")


@dataclass
class StealthConfig:
    enabled: bool = os.getenv("STEALTH_ENABLED", "true").lower() == "true"
    human_simulation: bool = os.getenv("HUMAN_SIMULATION", "true").lower() == "true"
    delay_min: int = 1000
    delay_max: int = 3000
    max_retries: int = int(os.getenv("MAX_RETRIES_ON_BLOCK", "3"))

    def __post_init__(self):
        delay_range = os.getenv("REQUEST_DELAY_RANGE", "1000,3000")
        parts = delay_range.split(",")
        self.delay_min = int(parts[0])
        self.delay_max = int(parts[1]) if len(parts) > 1 else self.delay_min * 3


@dataclass
class OutputConfig:
    dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./data/output")))
    format: str = os.getenv("OUTPUT_FORMAT", "markdown")
    include_meta: bool = os.getenv("OUTPUT_INCLUDE_META", "true").lower() == "true"


@dataclass
class AppConfig:
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    firecrawl_host: str = os.getenv("FIRECRAWL_HOST", "http://localhost:3002")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "fc-local-dev")
    crawl4ai_base_url: str = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")
    crawl4ai_strategy: str = os.getenv("CRAWL4AI_DEFAULT_STRATEGY", "pruning")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "./data/scraper.log")


config = AppConfig()
