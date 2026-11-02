from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.relative_locator import locate_with

from pages.base_page import BasePage, by_test_id
from utils.money import parse_money


def product_slug(product_name: str) -> str:
    """The site builds button ids from the product name.

    "Sauce Labs Backpack" becomes "add-to-cart-sauce-labs-backpack".
    """
    return product_name.lower().replace(" ", "-")


class InventoryPage(BasePage):
    URL_PATH = "/inventory.html"
    READY_LOCATOR = by_test_id("inventory-list")

    SORT_SELECT = by_test_id("product-sort-container")
    ACTIVE_SORT = by_test_id("active-option")
    ITEM_NAMES = by_test_id("inventory-item-name")
    ITEM_PRICES = by_test_id("inventory-item-price")
    CART_LINK = by_test_id("shopping-cart-link")
    CART_BADGE = by_test_id("shopping-cart-badge")
    # The data-test attribute "open-menu" sits on a decorative image. The real
    # control is a transparent button laid over it, so we target the button.
    # Lesson: always check which element receives the click, not which one
    # carries the test id.
    MENU_BUTTON = (By.ID, "react-burger-menu-btn")
    LOGOUT_LINK = by_test_id("logout-sidebar-link")

    # Sort option values used by the select element
    SORT_NAME_A_TO_Z = "az"
    SORT_NAME_Z_TO_A = "za"
    SORT_PRICE_LOW_TO_HIGH = "lohi"
    SORT_PRICE_HIGH_TO_LOW = "hilo"

    # Reading the page

    def product_names(self) -> list[str]:
        return self.texts_of(self.ITEM_NAMES)

    def product_prices(self) -> list[float]:
        return [parse_money(text) for text in self.texts_of(self.ITEM_PRICES)]

    def price_of(self, product_name: str) -> float:
        """Find the price shown under a product name with a relative locator.

        Selenium 4 relative locators describe position on screen. The price
        of a product is the price element closest below its name element.
        """
        name_element = self._name_element(product_name)
        price_locator = locate_with(By.CSS_SELECTOR, "[data-test='inventory-item-price']").below(name_element)
        return parse_money(self.driver.find_element(price_locator).text)

    def cart_count(self) -> int:
        """Number shown on the cart badge. Zero when the badge is absent."""
        if self.is_visible(self.CART_BADGE, timeout=1):
            return int(self.text_of(self.CART_BADGE))
        return 0

    def active_sort_label(self) -> str:
        return self.text_of(self.ACTIVE_SORT)

    # Actions

    def sort_by(self, option_value: str) -> "InventoryPage":
        self.select_by_value(self.SORT_SELECT, option_value)
        return self

    def add_to_cart(self, product_name: str) -> "InventoryPage":
        slug = product_slug(product_name)
        self.click(by_test_id(f"add-to-cart-{slug}"))
        # The button flips to "Remove" once the store updates. Wait for it so
        # the next assertion does not run against a stale state.
        self.wait_visible(by_test_id(f"remove-{slug}"))
        return self

    def remove_from_cart(self, product_name: str) -> "InventoryPage":
        slug = product_slug(product_name)
        self.click(by_test_id(f"remove-{slug}"))
        self.wait_visible(by_test_id(f"add-to-cart-{slug}"))
        return self

    def open_cart(self):
        from pages.cart_page import CartPage

        self.click_and_wait_for_url(self.CART_LINK, "/cart.html")
        return CartPage(self.driver, self.base_url).wait_until_loaded()

    def logout(self):
        from pages.login_page import LoginPage

        self.click(self.MENU_BUTTON)
        self.click(self.LOGOUT_LINK)
        return LoginPage(self.driver, self.base_url).wait_until_loaded()

    # Internals

    def _name_element(self, product_name: str) -> WebElement:
        for element in self.find_all(self.ITEM_NAMES):
            if element.text.strip() == product_name:
                return element
        raise TimeoutException(f"Product not listed: {product_name}")

    def wait_for_sort(self, expected_label: str) -> None:
        self.wait.until(EC.text_to_be_present_in_element(self.ACTIVE_SORT, expected_label))
