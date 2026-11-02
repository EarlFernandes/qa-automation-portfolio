import { test, expect, signedOutState } from '../src/fixtures/test';
import { usersThatCanLogIn } from '../src/data/users';

// These tests exercise the login form itself, so they start without the saved session.
test.use({ storageState: signedOutState });

test.describe('Login', () => {
  test.beforeEach(async ({ loginPage }) => {
    await loginPage.goto();
  });

  test('standard user can sign in', { tag: ['@smoke'] }, async ({ loginPage, inventoryPage, users }) => {
    await loginPage.login(users.standard);

    await expect(inventoryPage.title).toHaveText('Products');
    await expect(inventoryPage.items).toHaveCount(6);
  });

  test('locked out user sees a lock-out message', { tag: ['@regression'] }, async ({ page, loginPage, users }) => {
    await loginPage.login(users.lockedOut);

    await expect(loginPage.errorMessage).toHaveText('Epic sadface: Sorry, this user has been locked out.');
    await expect(page).toHaveURL('/');
  });

  test('wrong password is rejected', { tag: ['@regression'] }, async ({ loginPage, users }) => {
    await loginPage.loginWith(users.standard.username, 'not-the-password');

    await expect(loginPage.errorMessage).toHaveText(
      'Epic sadface: Username and password do not match any user in this service',
    );
  });

  test('empty username is rejected', { tag: ['@regression'] }, async ({ loginPage, users }) => {
    await loginPage.loginWith('', users.standard.password);

    await expect(loginPage.errorMessage).toHaveText('Epic sadface: Username is required');
  });

  test('empty password is rejected', { tag: ['@regression'] }, async ({ loginPage, users }) => {
    await loginPage.loginWith(users.standard.username, '');

    await expect(loginPage.errorMessage).toHaveText('Epic sadface: Password is required');
  });

  // Data-driven: one test per account the site accepts.
  for (const user of usersThatCanLogIn) {
    test(`${user.username} can sign in`, { tag: ['@regression'] }, async ({ loginPage, inventoryPage }) => {
      await loginPage.login(user);

      await expect(inventoryPage.title).toHaveText('Products');
      await expect(inventoryPage.items).toHaveCount(6);
    });
  }

  test('login form has the expected accessible structure', { tag: ['@regression'] }, async ({ loginPage }) => {
    // An aria snapshot checks roles and names, not pixels, so it survives restyling.
    await expect(loginPage.form).toMatchAriaSnapshot(`
      - form "Login":
        - textbox "Username"
        - textbox "Password"
        - button "Login"
    `);
  });

  test('signed-out visitor is sent back to the login page', { tag: ['@regression'] }, async ({
    page,
    loginPage,
    inventoryPage,
  }) => {
    await inventoryPage.goto();

    await expect(page).toHaveURL('/');
    await expect(loginPage.errorMessage).toHaveText(
      "Epic sadface: You can only access '/inventory.html' when you are logged in.",
    );
  });
});
