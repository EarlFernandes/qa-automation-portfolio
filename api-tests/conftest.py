"""Shared fixtures for the API contract tests.

Targets:
- REST: https://dummyjson.com (public fake store API with auth, products, carts)
- GraphQL: https://countries.trevorblades.com (public countries API)

Override the REST base URL with API_BASE_URL and the GraphQL URL with
GRAPHQL_URL to point the same tests at another environment.

The login account (emilys / emilyspass) is published in the DummyJSON docs. It
is a public demo account, not a secret.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).parent / "schemas"

DEMO_USERNAME = "emilys"
DEMO_PASSWORD = "emilyspass"


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("API_BASE_URL", "https://dummyjson.com").rstrip("/")


@pytest.fixture(scope="session")
def graphql_url() -> str:
    return os.getenv("GRAPHQL_URL", "https://countries.trevorblades.com/")


@pytest.fixture(scope="session")
def client(base_url: str):
    """One HTTP client for the whole session. Connections are reused."""
    headers = {"Accept": "application/json", "User-Agent": "qa-automation-portfolio/1.0"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=15.0) as http:
        yield http


@pytest.fixture
def anonymous_client(base_url: str):
    """A fresh client with an empty cookie jar.

    The login call stores session cookies in the shared client, and the API
    accepts those cookies as credentials. Negative auth tests must not inherit
    them, or a 200 would hide a missing 401.
    """
    with httpx.Client(base_url=base_url, headers={"Accept": "application/json"}, timeout=15.0) as http:
        yield http


@pytest.fixture(scope="session")
def auth_token(client: httpx.Client) -> str:
    response = client.post(
        "/auth/login",
        json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD, "expiresInMins": 30},
    )
    assert response.status_code == 200, f"Login failed: {response.status_code} {response.text}"
    return response.json()["accessToken"]


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    """Read schemas/<name>.schema.json once per session."""
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def schema_registry() -> Registry:
    """Register every schema file so one schema can $ref another by its $id."""
    registry = Registry()
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def assert_matches_schema(payload: object, schema_name: str) -> None:
    """Validate a payload and report every violation, not only the first."""
    validator = Draft202012Validator(load_schema(schema_name), registry=schema_registry())
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"- {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
        raise AssertionError(f"Payload does not match {schema_name}.schema.json:\n" + "\n".join(lines))


@pytest.fixture
def graphql(graphql_url: str):
    """Small helper that posts a GraphQL query and returns the parsed body."""

    def run(query: str, variables: dict | None = None) -> dict:
        response = httpx.post(
            graphql_url,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        assert response.status_code == 200, f"GraphQL HTTP {response.status_code}: {response.text}"
        body = response.json()
        assert "errors" not in body, f"GraphQL errors: {body['errors']}"
        return body["data"]

    return run
