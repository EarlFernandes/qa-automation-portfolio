from __future__ import annotations

from pages.base_page import BasePage, by_test_id
from pages.checkout_pages import CheckoutInformationPage


class CartPage(BasePage):
    URL_PATH = "/cart.html"
    READY_LOCATOR = by_test_id("cart-list")

    ITEM_NAMES = by_test_id("inventory-item-name")
    ITEM_QUANTITIES = by_test_id("item-quantity")
    CHECKOUT_BUTTON = by_test_id("checkout")
    CONTINUE_SHOPPING = by_test_id("continue-shopping")

    def item_names(self) -> list[str]:
        return self.texts_of(self.ITEM_NAMES)

    def item_quantities(self) -> list[int]:
        return [int(text) for text in self.texts_of(self.ITEM_QUANTITIES)]

    def checkout(self) -> CheckoutInformationPage:
        self.click_and_wait_for_url(self.CHECKOUT_BUTTON, "/checkout-step-one.html")
        return CheckoutInformationPage(self.driver, self.base_url).wait_until_loaded()
