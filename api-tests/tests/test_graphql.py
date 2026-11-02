import pytest

COUNTRY_QUERY = """
query Country($code: ID!) {
  country(code: $code) {
    code
    name
    capital
    currency
    continent { code name }
  }
}
"""

COUNTRIES_BY_CONTINENT = """
query ByContinent($continent: String!) {
  countries(filter: { continent: { eq: $continent } }) {
    code
    continent { code }
  }
}
"""


@pytest.mark.smoke
def test_country_query_returns_the_expected_fields(graphql):
    data = graphql(COUNTRY_QUERY, {"code": "CA"})

    country = data["country"]
    assert country["code"] == "CA"
    assert country["name"] == "Canada"
    assert country["capital"] == "Ottawa"
    assert country["currency"] == "CAD"
    assert country["continent"] == {"code": "NA", "name": "North America"}


@pytest.mark.regression
def test_unknown_country_code_returns_null_not_an_error(graphql):
    data = graphql(COUNTRY_QUERY, {"code": "ZZ"})

    assert data["country"] is None


@pytest.mark.regression
def test_continent_filter_returns_only_that_continent(graphql):
    data = graphql(COUNTRIES_BY_CONTINENT, {"continent": "EU"})

    countries = data["countries"]
    assert len(countries) > 40
    assert {country["continent"]["code"] for country in countries} == {"EU"}
