import pytest

from conftest import assert_matches_schema

NEW_CART = {"userId": 1, "products": [{"id": 1, "quantity": 2}, {"id": 5, "quantity": 1}]}


@pytest.fixture(scope="module")
def created_cart(client):
    """POST /carts/add simulates a create. The API returns the computed cart."""
    response = client.post("/carts/add", json=NEW_CART)
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.mark.smoke
def test_created_cart_matches_schema(created_cart):
    assert_matches_schema(created_cart, "cart")
    assert created_cart["userId"] == NEW_CART["userId"]


@pytest.mark.regression
def test_created_cart_keeps_the_requested_lines(created_cart):
    requested = {line["id"]: line["quantity"] for line in NEW_CART["products"]}
    returned = {line["id"]: line["quantity"] for line in created_cart["products"]}

    assert returned == requested


@pytest.mark.regression
def test_cart_totals_add_up(created_cart):
    lines = created_cart["products"]

    for line in lines:
        assert line["total"] == pytest.approx(line["price"] * line["quantity"], abs=0.01)
        assert line["discountedPrice"] <= line["total"]

    assert created_cart["totalProducts"] == len(lines)
    assert created_cart["totalQuantity"] == sum(line["quantity"] for line in lines)
    assert created_cart["total"] == pytest.approx(sum(line["total"] for line in lines), abs=0.01)
    # The API rounds the discounted total to whole units, so allow one unit.
    assert created_cart["discountedTotal"] == pytest.approx(
        sum(line["discountedPrice"] for line in lines), abs=1.0
    )
    assert created_cart["discountedTotal"] <= created_cart["total"]
