# API contract tests (Python, pytest, httpx, JSON Schema)

Contract and behaviour tests for two public APIs:

- REST: [DummyJSON](https://dummyjson.com/docs), a fake store API with
  authentication, products and carts.
- GraphQL: [Countries](https://countries.trevorblades.com), a public
  countries API.

19 tests. They run in about 3 seconds.

The login account (`emilys` / `emilyspass`) comes from the DummyJSON
documentation. It is a public demo account, not a secret.

## Run it

```bash
cd api-tests
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                 # all tests
pytest -m smoke        # fast checks only
pytest -m regression   # calculations and error handling
```

Results go to `results/junit.xml`.

Point the suite at another environment with environment variables:

| Variable | Default |
|---|---|
| `API_BASE_URL` | `https://dummyjson.com` |
| `GRAPHQL_URL` | `https://countries.trevorblades.com/` |

## Layout

```
api-tests/
├── conftest.py            shared client, auth fixtures, schema validation helper
├── schemas/               JSON Schema files (draft 2020-12)
│   ├── product.schema.json
│   ├── products_page.schema.json   references product.schema.json
│   ├── auth_user.schema.json
│   ├── user.schema.json
│   └── cart.schema.json
└── tests/
    ├── test_auth.py        login, current user, three negative cases
    ├── test_products.py    pagination math, schema by id, search, category, 404, response time
    ├── test_carts.py       simulated create, line and cart totals
    └── test_graphql.py     query by code, null for unknown code, continent filter
```

## Approach

Each response is checked at three levels:

1. Status code.
2. Shape, through a JSON Schema. The helper reports every violation in one
   assertion message, not only the first.
3. Business rules, such as `total == sum(line totals)` and
   `skip=20` returning product 21 first.

Schemas live as files, not inline dicts. A file is easy to diff when the API
changes, easy to share with the backend team, and can be generated from an
OpenAPI document later. One schema can reference another through its `$id`,
so the product shape is defined once and reused by the list schema.

Two HTTP clients exist on purpose. The shared session client reuses
connections and carries the cookies set at login. The anonymous client has an
empty cookie jar and is used for negative authentication tests. Without it,
the API would accept the login cookie and a missing 401 would never be
noticed. That is a real class of false positive in API suites.

Tolerances are explicit. Money comparisons use `pytest.approx` with an absolute
tolerance of one cent. The discounted cart total is rounded to whole units by
the API, so that one check allows one unit.

The response time check is a smoke level guard, not a performance test. Load
and latency percentiles are covered by the JMeter plan in `../jmeter`.
