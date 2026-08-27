import { test, expect } from "@playwright/test";

/**
 * End-to-end smoke tests covering the highest-value user flows through a
 * real browser against a real (test) backend. These complement, not
 * replace, the Vitest component tests and the Pytest integration suite -
 * see docs/TEST_REPORT.md.
 */

test.describe("public site", () => {
  test("home page loads and links to the catalogue", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Rockstar Organics/i);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("product catalogue renders without a console error", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.goto("/products");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("contact page submits a real enquiry end-to-end", async ({ page }) => {
    await page.goto("/contact");
    await page.getByLabel(/your name/i).fill("Playwright E2E");
    await page.getByLabel(/message/i).fill("Automated smoke test enquiry - safe to ignore.");
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /submit enquiry/i }).click();
    await expect(page.getByText(/reference number/i)).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("authentication", () => {
  const uniqueEmail = `e2e-${Date.now()}@example.com`;

  test("a farmer can register and land on their dashboard", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel(/full name/i).fill("E2E Farmer");
    await page.getByLabel(/^email/i).fill(uniqueEmail);
    await page.getByLabel(/phone/i).fill("9876543210");
    await page.getByLabel(/^password/i).fill("CorrectHorseBattery9!");
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/farmer/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: /welcome, e2e farmer/i })).toBeVisible();
  });

  test("an invalid login shows a generic error, not a stack trace", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/^email/i).fill("nobody@example.com");
    await page.getByLabel(/^password/i).fill("wrong-password-123");
    await page.getByRole("button", { name: /log in|sign in/i }).click();
    await expect(page.getByText(/invalid|incorrect|could not/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/traceback|internal server error/i)).toHaveCount(0);
  });
});

test.describe("resilience", () => {
  test("an unknown route renders the 404 page instead of a blank screen", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByText(/not found/i)).toBeVisible();
  });
});

test.describe("real-world content pass", () => {
  test("a distributor can submit an application and get a reference number", async ({ page }) => {
    await page.goto("/distributors");
    await page.getByLabel(/contact person/i).fill("Playwright Distributor");
    await page.getByLabel(/business name/i).fill("Playwright Distribution Co");
    await page.getByLabel(/^email/i).fill(`e2e-dist-${Date.now()}@example.com`);
    await page.getByLabel(/phone/i).fill("9876543215");
    await page.getByLabel(/requested territory/i).fill("Hyderabad");
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /submit application/i }).click();
    await expect(page.getByText(/reference number/i)).toBeVisible({ timeout: 10_000 });
  });

  test("OTP signup issues a dev code and creates the account on verification", async ({ page }) => {
    await page.goto("/signup");
    await page.getByLabel(/full name/i).fill("Playwright OTP Farmer");
    await page.getByLabel(/^email/i).fill(`e2e-otp-${Date.now()}@example.com`);
    await page.getByLabel(/phone/i).fill("9876543216");
    await page.getByLabel(/^password/i).fill("CorrectHorseBattery9!");
    await page.getByRole("button", { name: /send verification code/i }).click();

    const devCode = page.getByText(/your code is/i);
    await expect(devCode).toBeVisible({ timeout: 10_000 });
    const codeText = await devCode.textContent();
    const code = codeText?.match(/(\d{6})/)?.[1];
    expect(code).toBeTruthy();

    await page.getByLabel(/verification code/i).fill(code!);
    await page.getByRole("button", { name: /verify and create account/i }).click();
    await expect(page).toHaveURL(/\/farmer/, { timeout: 10_000 });
  });

  test("the certificates and gallery pages render without a console error", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.goto("/certificates");
    await expect(page.getByRole("heading", { name: /certificates/i })).toBeVisible();
    await page.goto("/gallery");
    await expect(page.getByRole("heading", { name: /gallery/i })).toBeVisible();
    expect(errors).toEqual([]);
  });
});
