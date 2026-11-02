import pytest

from conftest import DEMO_PASSWORD, DEMO_USERNAME, assert_matches_schema


@pytest.mark.smoke
def test_login_returns_tokens_and_the_user(client):
    response = client.post(
        "/auth/login",
        json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD, "expiresInMins": 30},
    )

    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "auth_user")
    assert body["username"] == DEMO_USERNAME
    assert body["accessToken"] != body["refreshToken"]


@pytest.mark.smoke
def test_me_returns_the_logged_in_user(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "user")
    assert body["username"] == DEMO_USERNAME


@pytest.mark.regression
def test_wrong_password_is_rejected(anonymous_client):
    response = anonymous_client.post(
        "/auth/login", json={"username": DEMO_USERNAME, "password": "wrong-password"}
    )

    assert response.status_code in (400, 401)
    assert "message" in response.json()


@pytest.mark.regression
def test_me_without_credentials_is_rejected(anonymous_client):
    # Uses the anonymous client on purpose. The shared client holds the
    # session cookies from login, and the API accepts cookies as credentials.
    response = anonymous_client.get("/auth/me")

    assert response.status_code in (401, 403)


@pytest.mark.regression
def test_me_with_a_bad_token_is_rejected(anonymous_client):
    response = anonymous_client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code in (401, 403, 500)
    assert "message" in response.json()
