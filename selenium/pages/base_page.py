"""Base class for all page objects.

Rules this class enforces:

1. Every interaction goes through an explicit wait. No raw find_element calls
   in tests, and no time.sleep.
2. Locators are tuples (By, value) stored on the page class, so a UI change is
   fixed in one place.
3. Each page knows one element that proves it rendered (READY_LOCATOR).
   wait_until_loaded() waits for it, which removes the race between a URL
   change and the first visible element of a single page app.
"""

from __future__ import annotations

from typing import Iterable

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

Locator = tuple[str, str]


def by_test_id(value: str) -> Locator:
    """The demo site marks elements with data-test attributes.

    A dedicated test attribute is the most stable locator: it does not change
    when the text, the CSS classes or the layout change.
    """
    return (By.CSS_SELECTOR, f"[data-test='{value}']")


class BasePage:
    URL_PATH = ""
    READY_LOCATOR: Locator | None = None
    DEFAULT_TIMEOUT = 10

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    # Navigation

    def open(self):
        self.driver.get(f"{self.base_url}{self.URL_PATH}")
        return self.wait_until_loaded()

    def wait_until_loaded(self):
        if self.READY_LOCATOR is not None:
            self.wait_visible(self.READY_LOCATOR)
        return self

    def wait_for_url_contains(self, fragment: str, timeout: int | None = None) -> None:
        WebDriverWait(self.driver, timeout or self.timeout).until(EC.url_contains(fragment))

    def click_and_wait_for_url(self, locator: Locator, url_fragment: str) -> None:
        """Click, then wait for the client side route to change.

        Single page apps can drop a click that lands while a component is
        re-rendering. The click is retried once if the URL did not change
        within a short window. Navigation here is idempotent, so a second
        click is safe.
        """
        self.click(locator)
        try:
            self.wait_for_url_contains(url_fragment, timeout=5)
        except TimeoutException:
            self.click(locator)
            self.wait_for_url_contains(url_fragment)

    # Element helpers

    def find(self, locator: Locator) -> WebElement:
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_all(self, locator: Locator) -> list[WebElement]:
        self.find(locator)
        return self.driver.find_elements(*locator)

    def wait_visible(self, locator: Locator) -> WebElement:
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_hidden(self, locator: Locator) -> bool:
        return self.wait.until(EC.invisibility_of_element_located(locator))

    def is_visible(self, locator: Locator, timeout: int = 2) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def click(self, locator: Locator) -> None:
        """Click once the element accepts the click.

        element_to_be_clickable only checks visible and enabled. An element can
        still be covered by an overlay or a menu that is sliding in. The wait
        below keeps trying until the click goes through or the timeout ends.
        """
        self.wait.until(EC.element_to_be_clickable(locator))

        def attempt(driver: WebDriver) -> bool:
            try:
                driver.find_element(*locator).click()
                return True
            except (
                ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(attempt, message=f"Click never succeeded on {locator}")

    def type(self, locator: Locator, text: str, clear: bool = True) -> None:
        element = self.wait_visible(locator)
        if clear:
            element.clear()
        element.send_keys(text)

    def text_of(self, locator: Locator) -> str:
        return self.wait_visible(locator).text.strip()

    def texts_of(self, locator: Locator) -> list[str]:
        return [element.text.strip() for element in self.find_all(locator)]

    def select_by_value(self, locator: Locator, value: str) -> None:
        Select(self.wait_visible(locator)).select_by_value(value)

    @staticmethod
    def first_text(elements: Iterable[WebElement]) -> str:
        for element in elements:
            return element.text.strip()
        return ""
