from __future__ import annotations

from pages.base_page import BasePage, by_test_id
from pages.inventory_page import InventoryPage


class LoginPage(BasePage):
    URL_PATH = "/"
    READY_LOCATOR = by_test_id("login-button")

    USERNAME = by_test_id("username")
    PASSWORD = by_test_id("password")
    LOGIN_BUTTON = by_test_id("login-button")
    ERROR = by_test_id("error")

    def login(self, username: str, password: str) -> InventoryPage:
        """Log in and return the inventory page, already loaded."""
        self.type(self.USERNAME, username)
        self.type(self.PASSWORD, password)
        self.click_and_wait_for_url(self.LOGIN_BUTTON, "/inventory.html")
        return InventoryPage(self.driver, self.base_url).wait_until_loaded()

    def login_expecting_error(self, username: str, password: str) -> str:
        """Submit credentials that must fail and return the error text."""
        if username:
            self.type(self.USERNAME, username)
        if password:
            self.type(self.PASSWORD, password)
        self.click(self.LOGIN_BUTTON)
        return self.text_of(self.ERROR)
