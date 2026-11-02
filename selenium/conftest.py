"""Shared pytest fixtures for the Selenium suite.

Configuration comes from environment variables so the same tests run on a
laptop and in CI without code changes:

    BASE_URL           target site, default https://www.saucedemo.com
    HEADLESS           1 (default) runs Chrome headless, 0 shows the browser
    CHROME_BINARY      optional path to a Chrome binary
    CHROMEDRIVER_PATH  optional path to a chromedriver binary

When CHROMEDRIVER_PATH is not set, Selenium Manager (built into Selenium 4)
downloads a driver that matches the installed Chrome. No manual driver setup.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

RESULTS_DIR = Path(__file__).parent / "results"
SCREENSHOT_DIR = RESULTS_DIR / "screenshots"

# Public demo accounts published by the Swag Labs demo site. Not secrets.
USERS = {
    "standard_user": "secret_sauce",
    "locked_out_user": "secret_sauce",
    "problem_user": "secret_sauce",
    "performance_glitch_user": "secret_sauce",
}


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "https://www.saucedemo.com").rstrip("/")


def _chrome_options() -> Options:
    options = Options()
    if os.getenv("HEADLESS", "1") != "0":
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-background-networking")
    options.add_argument("--no-first-run")
    binary = os.getenv("CHROME_BINARY")
    if binary:
        options.binary_location = binary
    return options


@pytest.fixture
def driver(request: pytest.FixtureRequest):
    """One fresh browser per test. Isolation beats speed for a UI suite."""
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    service = Service(driver_path) if driver_path else Service()
    browser = webdriver.Chrome(options=_chrome_options(), service=service)
    browser.set_page_load_timeout(30)
    yield browser

    # Save a screenshot when the test body failed. The flag is set by the
    # pytest_runtest_makereport hook below.
    if getattr(request.node, "failed_in_call", False):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = SCREENSHOT_DIR / f"{request.node.name}-{stamp}.png"
        browser.save_screenshot(str(target))
        print(f"\nScreenshot saved: {target}")
    browser.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        item.failed_in_call = True


@pytest.fixture
def login_page(driver, base_url) -> LoginPage:
    return LoginPage(driver, base_url).open()


@pytest.fixture
def inventory_page(login_page) -> InventoryPage:
    """Logs in as the standard user and returns the loaded inventory page."""
    return login_page.login("standard_user", USERS["standard_user"])
