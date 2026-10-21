"""Tests for src/common/stealth.py — GREASE, _fpRand, profile consistency."""

import json
import re

import pytest

from src.common.stealth import (
    PROFILES,
    BrowserProfile,
    SessionFingerprint,
    _grease_brand,
    _grease_brands,
    grease_sec_ch_ua,
    navigator_stealth_script,
    random_user_agent,
    stealth_headers,
)


class TestBrowserProfile:
    def test_profiles_exist(self):
        assert len(PROFILES) >= 3

    def test_profiles_are_frozen(self):
        with pytest.raises(AttributeError):
            PROFILES[0].name = "modified"

    def test_profiles_are_consistent(self):
        for p in PROFILES:
            assert p.chrome_major in p.ua
            assert p.chrome_major in p.chrome_version
            assert not p.mobile
            assert p.viewport_width > 0
            assert p.viewport_height > 0

    def test_profile_platforms(self):
        names = {p.name for p in PROFILES}
        assert "chrome-win" in names
        assert "chrome-mac" in names
        assert "chrome-linux" in names

    def test_win_profile_ua_contains_windows(self):
        win = next(p for p in PROFILES if p.name == "chrome-win")
        assert "Windows NT" in win.ua
        assert win.platform == "Windows"

    def test_mac_profile_ua_contains_mac(self):
        mac = next(p for p in PROFILES if p.name == "chrome-mac")
        assert "Macintosh" in mac.ua
        assert mac.platform == "macOS"

    def test_linux_profile_ua_contains_linux(self):
        linux = next(p for p in PROFILES if p.name == "chrome-linux")
        assert "Linux" in linux.ua
        assert linux.platform == "Linux"


class TestSessionFingerprint:
    def test_deterministic_profile_selection(self):
        fp1 = SessionFingerprint(seed=42)
        fp2 = SessionFingerprint(seed=42)
        assert fp1.profile.name == fp2.profile.name

    def test_different_seeds_can_select_different_profiles(self):
        profiles_seen = set()
        for seed in range(100):
            fp = SessionFingerprint(seed=seed)
            profiles_seen.add(fp.profile.name)
        assert len(profiles_seen) > 1

    def test_seed_property(self):
        fp = SessionFingerprint(seed=12345)
        assert fp.seed == 12345

    def test_auto_seed(self):
        fp = SessionFingerprint()
        assert 0 <= fp.seed < 2**32

    def test_fp_rand_deterministic(self):
        fp = SessionFingerprint(seed=99)
        v1 = fp.fp_rand("canvas")
        v2 = fp.fp_rand("canvas")
        assert v1 == v2

    def test_fp_rand_different_salts(self):
        fp = SessionFingerprint(seed=99)
        assert fp.fp_rand("canvas") != fp.fp_rand("audio")

    def test_fp_rand_range(self):
        fp = SessionFingerprint(seed=0)
        for salt in ["canvas", "audio", "battery", "colordepth", "hw", "mem"]:
            val = fp.fp_rand(salt)
            assert 0.0 <= val < 1.0

    def test_fp_int_range(self):
        fp = SessionFingerprint(seed=77)
        for _ in range(20):
            val = fp.fp_int("test", 4, 16)
            assert 4 <= val <= 16

    def test_fp_int_deterministic(self):
        fp = SessionFingerprint(seed=77)
        assert fp.fp_int("test", 0, 100) == fp.fp_int("test", 0, 100)

    def test_canvas_noise_range(self):
        fp = SessionFingerprint(seed=1)
        assert 0.0 <= fp.canvas_noise() <= 0.02

    def test_audio_context_noise_range(self):
        fp = SessionFingerprint(seed=1)
        assert 0.0 <= fp.audio_context_noise() <= 0.0001

    def test_battery_level_range(self):
        fp = SessionFingerprint(seed=1)
        assert 0.5 <= fp.battery_level() <= 1.0

    def test_screen_color_depth_valid(self):
        fp = SessionFingerprint(seed=1)
        assert fp.screen_color_depth() in (24, 30, 32)


class TestGREASE:
    def test_grease_brand_contains_special_char(self):
        brand = _grease_brand(42, 0)
        assert brand.startswith("Not")
        assert "A" in brand
        assert "Brand" in brand
        has_special = any(c in brand for c in " (:-./);=?_")
        assert has_special

    def test_grease_brand_deterministic(self):
        assert _grease_brand(42, 0) == _grease_brand(42, 0)

    def test_grease_brand_varies_by_seed(self):
        brands = {_grease_brand(s, 0) for s in range(50)}
        assert len(brands) > 1

    def test_grease_brands_three_entries(self):
        fp = SessionFingerprint(seed=10)
        brands = _grease_brands(fp)
        assert len(brands) == 3

    def test_grease_brands_contain_chromium_and_chrome(self):
        fp = SessionFingerprint(seed=10)
        brands = _grease_brands(fp)
        brand_names = {b[0] for b in brands}
        assert "Chromium" in brand_names
        assert "Google Chrome" in brand_names

    def test_grease_brands_deterministic_order(self):
        fp = SessionFingerprint(seed=10)
        b1 = _grease_brands(fp)
        b2 = _grease_brands(fp)
        assert b1 == b2

    def test_grease_brands_order_varies_by_seed(self):
        orders = []
        for seed in range(50):
            fp = SessionFingerprint(seed=seed)
            brands = _grease_brands(fp)
            orders.append(tuple(b[0] for b in brands))
        assert len(set(orders)) > 1

    def test_grease_sec_ch_ua_format(self):
        fp = SessionFingerprint(seed=42)
        header = grease_sec_ch_ua(fp)
        parts = header.split(", ")
        assert len(parts) == 3
        for part in parts:
            assert re.match(r'"[^"]+";v="\d+"', part), f"Bad format: {part}"

    def test_grease_sec_ch_ua_matches_profile_version(self):
        fp = SessionFingerprint(seed=42)
        header = grease_sec_ch_ua(fp)
        assert fp.profile.chrome_major in header


class TestStealthHeaders:
    def test_headers_contain_required_keys(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        required = [
            "User-Agent", "Accept", "Accept-Language", "Accept-Encoding",
            "Sec-CH-UA", "Sec-CH-UA-Mobile", "Sec-CH-UA-Platform",
            "Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site",
        ]
        for key in required:
            assert key in h, f"Missing header: {key}"

    def test_headers_ua_matches_profile(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        assert h["User-Agent"] == fp.profile.ua

    def test_headers_platform_matches_profile(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        assert fp.profile.platform in h["Sec-CH-UA-Platform"]

    def test_headers_mobile_matches_profile(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        expected = "?1" if fp.profile.mobile else "?0"
        assert h["Sec-CH-UA-Mobile"] == expected

    def test_headers_sec_ch_ua_matches_grease(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        assert h["Sec-CH-UA"] == grease_sec_ch_ua(fp)

    def test_headers_referer_sets_same_origin(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp, referer="https://example.com")
        assert h["Referer"] == "https://example.com"
        assert h["Sec-Fetch-Site"] == "same-origin"

    def test_headers_no_referer_is_none(self):
        fp = SessionFingerprint(seed=1)
        h = stealth_headers(fp)
        assert h["Sec-Fetch-Site"] == "none"
        assert "Referer" not in h

    def test_headers_without_fp_works(self):
        h = stealth_headers()
        assert "User-Agent" in h
        assert "Sec-CH-UA" in h

    def test_headers_are_consistent_per_session(self):
        fp = SessionFingerprint(seed=42)
        h1 = stealth_headers(fp)
        h2 = stealth_headers(fp)
        assert h1 == h2


class TestNavigatorStealthScript:
    def test_script_is_valid_js_structure(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert script.startswith("(")
        assert script.strip().endswith("})();")

    def test_script_contains_webdriver_false(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert "webdriver" in script
        assert "false" in script

    def test_script_contains_prototype_placement(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert "Object.getPrototypeOf(navigator)" in script
        assert "Object.defineProperty(proto" in script

    def test_script_contains_plugins(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert "PDF Viewer" in script
        assert "Chrome PDF Viewer" in script
        assert "pluginData" in script

    def test_script_contains_user_agent_data(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert "userAgentData" in script
        assert fp.profile.platform in script
        assert fp.profile.chrome_version in script

    def test_script_brands_match_headers(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        header_brands = _grease_brands(fp)
        for brand, version in header_brands:
            assert brand in script

    def test_script_hardware_from_fp(self):
        fp = SessionFingerprint(seed=42)
        hw = fp.fp_int("hwconcurrency", 4, 16)
        script = navigator_stealth_script(fp)
        assert f"get: () => {hw}" in script

    def test_script_platform_matches_profile(self):
        fp = SessionFingerprint(seed=42)
        script = navigator_stealth_script(fp)
        assert f'platform: "{fp.profile.platform}"' in script
        assert f'platformVersion: "{fp.profile.platform_version}"' in script
        assert f'architecture: "{fp.profile.architecture}"' in script


class TestBackwardCompatibility:
    def test_random_user_agent_returns_string(self):
        ua = random_user_agent()
        assert isinstance(ua, str)
        assert "Mozilla" in ua

    def test_random_user_agent_from_profiles(self):
        valid_uas = {p.ua for p in PROFILES}
        for _ in range(20):
            assert random_user_agent() in valid_uas

    def test_stealth_headers_no_args(self):
        h = stealth_headers()
        assert isinstance(h, dict)
        assert "User-Agent" in h
