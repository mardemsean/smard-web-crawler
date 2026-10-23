"""Stealth utilities for HTTP and Playwright-based scraping.

Three anti-detection patterns extracted from Obscura headless engine:
1. GREASE sec-ch-ua brand shuffling for header consistency
2. Per-session seeded fingerprint noise (_fpRand model)
3. Consistent browser profiles (UA, platform, headers agree across surfaces)

See RESEARCH/PONTE-Obscura-Stealth.md for the full bridge document.
"""

import hashlib
import json
import platform
import random
from dataclasses import dataclass
from typing import Optional

_GREASE_CHARS = " (:-./);=?_"


@dataclass(frozen=True)
class BrowserProfile:
    """Internally consistent browser identity.

    All fields agree: the UA string implies the same platform, architecture,
    and browser version as the sec-ch-ua brands and client hints.
    """

    name: str
    ua: str
    platform: str
    platform_version: str
    architecture: str
    bitness: str
    chrome_version: str
    chrome_major: str
    mobile: bool
    viewport_width: int
    viewport_height: int

    @property
    def navigator_platform(self) -> str:
        """`navigator.platform` value a real Chrome reports for this profile."""
        if self.platform == "Windows":
            return "Win32"
        if self.platform == "macOS":
            return "MacIntel"
        return "Linux aarch64" if self.architecture == "arm" else "Linux x86_64"


PROFILES: list[BrowserProfile] = [
    BrowserProfile(
        name="chrome-win",
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        platform="Windows",
        platform_version="15.0.0",
        architecture="x86",
        bitness="64",
        chrome_version="129.0.6668.71",
        chrome_major="129",
        mobile=False,
        viewport_width=1920,
        viewport_height=1080,
    ),
    BrowserProfile(
        name="chrome-mac",
        ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        platform="macOS",
        platform_version="14.7.0",
        architecture="arm",
        bitness="64",
        chrome_version="129.0.6668.71",
        chrome_major="129",
        mobile=False,
        viewport_width=1512,
        viewport_height=982,
    ),
    BrowserProfile(
        name="chrome-linux",
        ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        platform="Linux",
        platform_version="6.5.0",
        architecture="x86",
        bitness="64",
        chrome_version="129.0.6668.71",
        chrome_major="129",
        mobile=False,
        viewport_width=1920,
        viewport_height=1080,
    ),
]


class SessionFingerprint:
    """Per-session deterministic fingerprint noise, modeled after Obscura's _fpRand.

    Each session gets a unique seed. All fingerprint-surface values derived from
    the same seed are internally consistent within the session but vary across
    sessions, defeating cross-session correlation.
    """

    def __init__(self, seed: Optional[int] = None, profile_name: Optional[str] = None):
        self._seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        self._rng = random.Random(self._seed)
        chosen = self._rng.choice(PROFILES)
        if profile_name is not None:
            chosen = next((p for p in PROFILES if p.name == profile_name), None)
            if chosen is None:
                raise ValueError(f"unknown profile {profile_name!r}; choose from {[p.name for p in PROFILES]}")
        self.profile: BrowserProfile = chosen

    @property
    def seed(self) -> int:
        return self._seed

    def fp_rand(self, salt: str) -> float:
        """Deterministic random float in [0, 1) for a fingerprint surface."""
        h = hashlib.sha256(f"{self._seed}:{salt}".encode()).digest()
        return int.from_bytes(h[:4], "big") / 2**32

    def fp_int(self, salt: str, lo: int, hi: int) -> int:
        """Deterministic random int in [lo, hi] for a fingerprint surface."""
        return lo + int(self.fp_rand(salt) * (hi - lo + 1))

    def canvas_noise(self) -> float:
        return self.fp_rand("canvas") * 0.02

    def audio_context_noise(self) -> float:
        return self.fp_rand("audio") * 0.0001

    def battery_level(self) -> float:
        return 0.5 + self.fp_rand("battery") * 0.5

    def screen_color_depth(self) -> int:
        return [24, 30, 32][self.fp_int("colordepth", 0, 2)]


def _grease_brand(seed: int, index: int) -> str:
    """Generate a GREASE brand string following Chrome's algorithm."""
    rng = random.Random(seed + index)
    char = rng.choice(_GREASE_CHARS)
    return f"Not{char}A{char}Brand"


def _grease_brands(fp: SessionFingerprint) -> list[tuple[str, str]]:
    """Build the three sec-ch-ua brands with GREASE shuffling."""
    profile = fp.profile
    grease = _grease_brand(fp.seed, 0)
    brands = [
        (grease, "24"),
        ("Chromium", profile.chrome_major),
        ("Google Chrome", profile.chrome_major),
    ]
    rng = random.Random(fp.seed)
    rng.shuffle(brands)
    return brands


def grease_sec_ch_ua(fp: SessionFingerprint) -> str:
    """Build sec-ch-ua header with GREASE brand shuffling."""
    return ", ".join(f'"{b}";v="{v}"' for b, v in _grease_brands(fp))


def stealth_headers(
    fp: Optional[SessionFingerprint] = None,
    referer: Optional[str] = None,
) -> dict[str, str]:
    """Generate stealth HTTP headers with full client-hint consistency.

    When called without a SessionFingerprint, creates a one-shot fingerprint
    for backward compatibility.
    """
    if fp is None:
        fp = SessionFingerprint()

    profile = fp.profile
    headers: dict[str, str] = {
        "User-Agent": profile.ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-CH-UA": grease_sec_ch_ua(fp),
        "Sec-CH-UA-Mobile": "?1" if profile.mobile else "?0",
        "Sec-CH-UA-Platform": f'"{profile.platform}"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    return headers


def host_profile_name(system: Optional[str] = None) -> str:
    """Profile matching the host OS. Web Workers keep the host's navigator.platform,
    so a profile from another OS leaves a main-thread/worker mismatch."""
    system = system or platform.system()
    return {"Windows": "chrome-win", "Darwin": "chrome-mac"}.get(system, "chrome-linux")


def random_user_agent() -> str:
    """Return a random user agent string (backward-compatible convenience)."""
    return random.choice(PROFILES).ua


_NAVIGATOR_STEALTH_JS = """\
(() => {
    const proto = Object.getPrototypeOf(navigator);
    const overrides = {
        webdriver: { get: () => false },
        hardwareConcurrency: { get: () => %(hw_concurrency)d },
        deviceMemory: { get: () => %(device_memory)d },
        maxTouchPoints: { get: () => 0 },
        languages: { get: () => Object.freeze(["en-US", "en"]) },
        platform: { get: () => "%(navigator_platform)s" },
    };
    for (const [prop, desc] of Object.entries(overrides)) {
        Object.defineProperty(proto, prop, { ...desc, configurable: true });
    }

    const pluginData = [
        {name: "PDF Viewer", filename: "internal-pdf-viewer"},
        {name: "Chrome PDF Viewer", filename: "internal-pdf-viewer"},
        {name: "Chromium PDF Viewer", filename: "internal-pdf-viewer"},
        {name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer"},
        {name: "WebKit built-in PDF", filename: "internal-pdf-viewer"},
    ];
    const plugins = Object.create(PluginArray.prototype);
    pluginData.forEach((p, i) => {
        const plug = Object.create(Plugin.prototype);
        Object.defineProperty(plug, 'name', {get: () => p.name});
        Object.defineProperty(plug, 'filename', {get: () => p.filename});
        Object.defineProperty(plug, 'description', {get: () => 'Portable Document Format'});
        Object.defineProperty(plugins, i, {value: plug, enumerable: true});
    });
    Object.defineProperties(plugins, {
        length: {get: () => pluginData.length},
        item: {value: (i) => plugins[i] || null},
        namedItem: {value: (n) => Array.prototype.find.call(plugins, p => p.name === n) || null},
        refresh: {value: () => {}},
    });
    Object.defineProperty(proto, 'plugins', {get: () => plugins, configurable: true});

    if ('userAgentData' in navigator) {
        const brands = %(brands_json)s;
        const uaData = {
            brands: brands,
            mobile: %(mobile)s,
            platform: "%(platform)s",
            getHighEntropyValues: (hints) => Promise.resolve({
                brands: brands,
                mobile: %(mobile)s,
                platform: "%(platform)s",
                platformVersion: "%(platform_version)s",
                architecture: "%(architecture)s",
                bitness: "%(bitness)s",
                fullVersionList: brands,
                model: "",
                uaFullVersion: "%(chrome_version)s",
            }),
        };
        Object.defineProperty(proto, 'userAgentData', {
            get: () => uaData,
            configurable: true,
        });
    }
})();
"""


def navigator_stealth_script(fp: SessionFingerprint) -> str:
    """Generate JS for Playwright page.add_init_script() navigator spoofing.

    Places navigator property overrides on the prototype chain (not as own
    properties) to avoid the hasOwnProperty bot-detection tell.
    """
    profile = fp.profile
    hw_conc = fp.fp_int("hwconcurrency", 4, 16)
    dev_mem = [4, 8, 16][fp.fp_int("devmem", 0, 2)]

    brands = _grease_brands(fp)
    brands_dicts = [{"brand": b, "version": v} for b, v in brands]

    return _NAVIGATOR_STEALTH_JS % {
        "hw_concurrency": hw_conc,
        "device_memory": dev_mem,
        "brands_json": json.dumps(brands_dicts),
        "mobile": "true" if profile.mobile else "false",
        "platform": profile.platform,
        "navigator_platform": profile.navigator_platform,
        "platform_version": profile.platform_version,
        "architecture": profile.architecture,
        "bitness": profile.bitness,
        "chrome_version": profile.chrome_version,
    }


async def simulate_human(
    page,
    fp: Optional[SessionFingerprint] = None,
) -> None:
    """Inject human-like behavior into a Playwright page.

    When a SessionFingerprint is provided, timing and movement parameters
    are derived from the session seed for consistency.
    """
    import asyncio

    rng = random.Random(fp.seed) if fp else random.Random()

    await asyncio.sleep(rng.uniform(0.5, 1.5))

    for _ in range(rng.randint(2, 5)):
        x = rng.randint(100, 800)
        y = rng.randint(100, 600)
        await page.mouse.move(x, y, steps=rng.randint(5, 15))
        await asyncio.sleep(rng.uniform(0.1, 0.3))

    scroll_amount = rng.randint(200, 600)
    await page.mouse.wheel(0, scroll_amount)
    await asyncio.sleep(rng.uniform(0.5, 1.0))
