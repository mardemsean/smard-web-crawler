"""Executes navigator_stealth_script in a real Chromium; skipped when Playwright is unavailable."""

import pytest
import pytest_asyncio

playwright = pytest.importorskip("playwright.async_api")

from smard_crawler.common.stealth import SessionFingerprint, host_profile_name, navigator_stealth_script


@pytest_asyncio.fixture
async def page():
    async with playwright.async_playwright() as pw:
        try:
            browser = await pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"chromium not launchable: {e}")
        fp = SessionFingerprint(seed=42, profile_name=host_profile_name())
        ctx = await browser.new_context(user_agent=fp.profile.ua)
        await ctx.add_init_script(navigator_stealth_script(fp))
        pg = await ctx.new_page()
        # userAgentData only exists in secure contexts, so serve over an intercepted https origin.
        await pg.route("https://stealth.test/", lambda r: r.fulfill(body="<p>x</p>", content_type="text/html"))
        await pg.goto("https://stealth.test/")
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_plugins_readable(page):
    assert await page.evaluate("navigator.plugins.length") == 5
    assert await page.evaluate("navigator.plugins instanceof PluginArray")
    assert await page.evaluate("navigator.plugins[0] instanceof Plugin")
    assert await page.evaluate("navigator.plugins.namedItem('Chrome PDF Viewer').name") == "Chrome PDF Viewer"


@pytest.mark.asyncio
async def test_webdriver_false_on_prototype(page):
    assert await page.evaluate("navigator.webdriver") is False
    assert await page.evaluate("Object.prototype.hasOwnProperty.call(navigator, 'webdriver')") is False


@pytest.mark.asyncio
async def test_user_agent_data_brands(page):
    brands = await page.evaluate("navigator.userAgentData.brands.map(b => b.brand)")
    assert "Google Chrome" in brands and "Chromium" in brands


@pytest.mark.asyncio
async def test_platform_coherent_with_ua_and_worker(page):
    fp = SessionFingerprint(seed=42, profile_name=host_profile_name())
    assert await page.evaluate("navigator.userAgent") == fp.profile.ua
    assert await page.evaluate("navigator.platform") == fp.profile.navigator_platform
    worker_platform = await page.evaluate("""() => new Promise(res => {
        const w = new Worker(URL.createObjectURL(new Blob(['postMessage(navigator.platform)'], {type: 'text/javascript'})));
        w.onmessage = e => res(e.data);
    })""")
    assert worker_platform == fp.profile.navigator_platform
