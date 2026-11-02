import pytest

from pages.inventory_page import InventoryPage

BACKPACK = "Sauce Labs Backpack"
BIKE_LIGHT = "Sauce Labs Bike Light"


@pytest.mark.smoke
def test_sort_by_price_low_to_high(inventory_page: InventoryPage):
    inventory_page.sort_by(InventoryPage.SORT_PRICE_LOW_TO_HIGH)
    inventory_page.wait_for_sort("Price (low to high)")

    prices = inventory_page.product_prices()
    assert prices == sorted(prices)
    assert len(prices) == 6


def test_sort_by_name_z_to_a(inventory_page: InventoryPage):
    inventory_page.sort_by(InventoryPage.SORT_NAME_Z_TO_A)
    inventory_page.wait_for_sort("Name (Z to A)")

    names = inventory_page.product_names()
    assert names == sorted(names, reverse=True)


def test_relative_locator_reads_the_price_under_a_product_name(inventory_page: InventoryPage):
    # The price shown under the name must match the price in the list at the
    # same position. This checks the relative locator against a plain read.
    names = inventory_page.product_names()
    prices = inventory_page.product_prices()
    expected = dict(zip(names, prices, strict=True))

    assert inventory_page.price_of(BACKPACK) == expected[BACKPACK]
    assert inventory_page.price_of(BIKE_LIGHT) == expected[BIKE_LIGHT]


@pytest.mark.smoke
def test_cart_badge_follows_add_and_remove(inventory_page: InventoryPage):
    assert inventory_page.cart_count() == 0

    inventory_page.add_to_cart(BACKPACK)
    assert inventory_page.cart_count() == 1

    inventory_page.add_to_cart(BIKE_LIGHT)
    assert inventory_page.cart_count() == 2

    inventory_page.remove_from_cart(BACKPACK)
    assert inventory_page.cart_count() == 1

    cart = inventory_page.open_cart()
    assert cart.item_names() == [BIKE_LIGHT]
    assert cart.item_quantities() == [1]
