import pytest

from conftest import USERS


@pytest.mark.smoke
@pytest.mark.parametrize("username", ["standard_user", "problem_user", "performance_glitch_user"])
def test_valid_users_reach_the_inventory(login_page, username):
    # performance_glitch_user logs in with a delay on purpose. The page object
    # waits for the inventory list, so no sleep is needed in the test.
    inventory = login_page.login(username, USERS[username])

    assert "/inventory.html" in inventory.driver.current_url
    assert len(inventory.product_names()) == 6


@pytest.mark.smoke
def test_locked_out_user_sees_a_clear_error(login_page):
    error = login_page.login_expecting_error("locked_out_user", USERS["locked_out_user"])

    assert error == "Epic sadface: Sorry, this user has been locked out."


def test_wrong_password_is_rejected(login_page):
    error = login_page.login_expecting_error("standard_user", "not-the-password")

    assert "Username and password do not match" in error


def test_empty_form_asks_for_username_first(login_page):
    error = login_page.login_expecting_error("", "")

    assert error == "Epic sadface: Username is required"


def test_logout_returns_to_the_login_page(inventory_page):
    login = inventory_page.logout()

    assert login.is_visible(login.LOGIN_BUTTON)
    assert login.driver.current_url.rstrip("/") == login.base_url
