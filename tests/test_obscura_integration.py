"""End-to-end: real `obscura serve --stealth` + ObscuraClient. Runs only when OBSCURA_BIN is set."""

import os
import subprocess

import pytest

from smard_crawler.bench.engines import _free_port, _wait_port
from smard_crawler.bench.run import start_fixture_server
from smard_crawler.browsers.client import ObscuraClient

OBSCURA_BIN = os.getenv("OBSCURA_BIN")
pytestmark = pytest.mark.skipif(not OBSCURA_BIN or not os.path.exists(OBSCURA_BIN or ""), reason="OBSCURA_BIN not set")


@pytest.mark.asyncio
async def test_obscura_client_scrapes_rendered_page():
    port = _free_port()
    proc = subprocess.Popen([OBSCURA_BIN, "serve", "--port", str(port), "--allow-private-network", "--stealth"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server, base = start_fixture_server()
    client = ObscuraClient(cdp_url=f"ws://127.0.0.1:{port}", token="")
    client.enabled = True
    try:
        await _wait_port(port, 30, proc)
        assert await client.health() is True
        static = await client.scrape(f"{base}/static.html")
        assert static["success"] and "SMARD-STATIC-MARKER" in static["markdown"]
        assert "Row 3 Col 2" in static["markdown"]
        assert len(static["links"]) == 4
        dynamic = await client.scrape(f"{base}/dynamic.html", wait_for=2000)
        for marker in ("SMARD-JS-MARKER", "SMARD-DELAYED-MARKER", "SMARD-FETCH-MARKER"):
            assert marker in dynamic["markdown"]
    finally:
        await client.close()
        server.shutdown()
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.asyncio
async def test_obscura_client_spawns_local_binary_on_demand(monkeypatch):
    monkeypatch.setenv("OBSCURA_ALLOW_PRIVATE_NETWORK", "1")
    port = _free_port()
    server, base = start_fixture_server()
    client = ObscuraClient(cdp_url=f"ws://127.0.0.1:{port}", token="", binary=OBSCURA_BIN)
    client.enabled = True
    try:
        assert await client.health() is True
        assert client._proc is not None and client._proc.returncode is None
        result = await client.scrape(f"{base}/static.html")
        assert "SMARD-STATIC-MARKER" in result["markdown"]
    finally:
        await client.close()
        server.shutdown()
    assert client._proc is None
