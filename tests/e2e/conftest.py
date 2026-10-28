"""Shared Playwright fixtures: a real server on a free port and a Chrome browser."""
import subprocess
import sys
import time
import urllib.request

import pytest

pw = pytest.importorskip("playwright.sync_api")
from backend import config  # noqa: E402
from tests.conftest import BASELINE, cleanup, counts  # noqa: E402

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="session")
def server():
    if not (config.NEO4J_URI and config.NEO4J_PASSWORD and config.APP_SECRET):
        pytest.skip("Neo4j credentials not configured")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            if urllib.request.urlopen(f"{BASE}/healthz", timeout=1).status == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("server did not start")
    cleanup()
    yield
    proc.terminate()
    cleanup()
    assert counts() == BASELINE


@pytest.fixture(scope="session")
def playwright_instance():
    with pw.sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    try:
        b = playwright_instance.chromium.launch(channel="chrome")
    except Exception:
        try:
            b = playwright_instance.chromium.launch()
        except Exception:
            pytest.skip("No Chrome/Chromium available for Playwright")
    yield b
    b.close()


def login(browser, email, **context_options):
    ctx = browser.new_context(**({"viewport": {"width": 1280, "height": 900}} | context_options))
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.fill("#email", email)
    page.click("button[type=submit]")
    page.wait_for_url(f"{BASE}/")
    return ctx, page
