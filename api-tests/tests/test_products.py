import pytest

from conftest import assert_matches_schema

RESPONSE_TIME_LIMIT_SECONDS = 3.0


@pytest.mark.smoke
def test_product_list_matches_schema_and_pagination_math(client):
    response = client.get("/products", params={"limit": 10, "skip": 20})

    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "products_page")
    assert body["limit"] == 10
    assert body["skip"] == 20
    assert len(body["products"]) == 10
    assert body["total"] >= 30, "the page we asked for must exist"
    ids = [product["id"] for product in body["products"]]
    assert ids == sorted(ids), "products come back in id order"
    assert ids[0] == 21, "skip=20 means the first product is number 21"


@pytest.mark.smoke
@pytest.mark.parametrize("product_id", [1, 50, 100])
def test_product_by_id_matches_schema(client, product_id):
    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "product")
    assert body["id"] == product_id


@pytest.mark.regression
def test_search_returns_only_matching_products(client):
    term = "phone"
    response = client.get("/products/search", params={"q": term, "limit": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    for product in body["products"]:
        haystack = " ".join(
            [product["title"], product["description"], product["category"], " ".join(product.get("tags", []))]
        ).lower()
        assert term in haystack, f"{product['title']!r} does not mention {term!r}"


@pytest.mark.regression
def test_category_filter_returns_only_that_category(client):
    response = client.get("/products/category/smartphones", params={"limit": 0})

    assert response.status_code == 200
    categories = {product["category"] for product in response.json()["products"]}
    assert categories == {"smartphones"}


@pytest.mark.regression
def test_unknown_product_returns_404_with_a_message(client):
    response = client.get("/products/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


@pytest.mark.regression
def test_product_list_responds_within_the_time_limit(client):
    response = client.get("/products", params={"limit": 30})

    assert response.status_code == 200
    assert response.elapsed.total_seconds() < RESPONSE_TIME_LIMIT_SECONDS, (
        f"took {response.elapsed.total_seconds():.2f}s"
    )
