"""The three checkout screens: information, overview, complete."""

from __future__ import annotations

from dataclasses import dataclass

from pages.base_page import BasePage, by_test_id
from utils.money import parse_money


@dataclass(frozen=True)
class Totals:
    item_total: float
    tax: float
    total: float


class CheckoutInformationPage(BasePage):
    URL_PATH = "/checkout-step-one.html"
    READY_LOCATOR = by_test_id("checkout-info-container")

    FIRST_NAME = by_test_id("firstName")
    LAST_NAME = by_test_id("lastName")
    POSTAL_CODE = by_test_id("postalCode")
    CONTINUE = by_test_id("continue")
    ERROR = by_test_id("error")

    def fill(self, first_name: str, last_name: str, postal_code: str) -> "CheckoutInformationPage":
        self.type(self.FIRST_NAME, first_name)
        self.type(self.LAST_NAME, last_name)
        self.type(self.POSTAL_CODE, postal_code)
        return self

    def submit(self) -> "CheckoutOverviewPage":
        self.click_and_wait_for_url(self.CONTINUE, "/checkout-step-two.html")
        return CheckoutOverviewPage(self.driver, self.base_url).wait_until_loaded()

    def submit_expecting_error(self) -> str:
        self.click(self.CONTINUE)
        return self.text_of(self.ERROR)


class CheckoutOverviewPage(BasePage):
    URL_PATH = "/checkout-step-two.html"
    READY_LOCATOR = by_test_id("checkout-summary-container")

    ITEM_NAMES = by_test_id("inventory-item-name")
    ITEM_PRICES = by_test_id("inventory-item-price")
    ITEM_QUANTITIES = by_test_id("item-quantity")
    SUBTOTAL = by_test_id("subtotal-label")
    TAX = by_test_id("tax-label")
    TOTAL = by_test_id("total-label")
    FINISH = by_test_id("finish")

    def item_names(self) -> list[str]:
        return self.texts_of(self.ITEM_NAMES)

    def line_totals(self) -> list[float]:
        prices = [parse_money(text) for text in self.texts_of(self.ITEM_PRICES)]
        quantities = [int(text) for text in self.texts_of(self.ITEM_QUANTITIES)]
        return [round(price * quantity, 2) for price, quantity in zip(prices, quantities, strict=True)]

    def totals(self) -> Totals:
        return Totals(
            item_total=parse_money(self.text_of(self.SUBTOTAL)),
            tax=parse_money(self.text_of(self.TAX)),
            total=parse_money(self.text_of(self.TOTAL)),
        )

    def finish(self) -> "CheckoutCompletePage":
        self.click_and_wait_for_url(self.FINISH, "/checkout-complete.html")
        return CheckoutCompletePage(self.driver, self.base_url).wait_until_loaded()


class CheckoutCompletePage(BasePage):
    URL_PATH = "/checkout-complete.html"
    READY_LOCATOR = by_test_id("complete-header")

    HEADER = by_test_id("complete-header")
    TEXT = by_test_id("complete-text")
    BACK_HOME = by_test_id("back-to-products")

    def header(self) -> str:
        return self.text_of(self.HEADER)

    def message(self) -> str:
        return self.text_of(self.TEXT)
