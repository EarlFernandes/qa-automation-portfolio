import pytest

from pages.inventory_page import InventoryPage

TAX_RATE = 0.08
ITEMS = ["Sauce Labs Backpack", "Sauce Labs Bolt T-Shirt", "Sauce Labs Onesie"]


@pytest.mark.regression
def test_full_purchase_shows_confirmation_and_correct_totals(inventory_page: InventoryPage):
    for item in ITEMS:
        inventory_page.add_to_cart(item)

    cart = inventory_page.open_cart()
    assert sorted(cart.item_names()) == sorted(ITEMS)

    overview = cart.checkout().fill("Ada", "Lovelace", "M5V 1A1").submit()
    assert sorted(overview.item_names()) == sorted(ITEMS)

    totals = overview.totals()
    expected_item_total = round(sum(overview.line_totals()), 2)
    expected_tax = round(expected_item_total * TAX_RATE, 2)

    assert totals.item_total == expected_item_total
    assert totals.tax == expected_tax
    assert totals.total == round(expected_item_total + expected_tax, 2)

    complete = overview.finish()
    assert complete.header() == "Thank you for your order!"
    assert "Your order has been dispatched" in complete.message()


@pytest.mark.regression
def test_checkout_rejects_missing_first_name(inventory_page: InventoryPage):
    inventory_page.add_to_cart(ITEMS[0])
    information = inventory_page.open_cart().checkout()

    error = information.fill("", "Lovelace", "M5V 1A1").submit_expecting_error()

    assert error == "Error: First Name is required"
