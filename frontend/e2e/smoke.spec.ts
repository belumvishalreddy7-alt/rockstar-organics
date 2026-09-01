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

  test("forgot-password never silently appears to succeed with no feedback", async ({ page }) => {
    // This test environment has no real email provider configured, so
    // email_sent always comes back false. If DEV_EXPOSE_RESET_TOKEN is on
    // (true here and in CI), the UI shows a working dev link instead of
    // the "could not confirm delivery" note - showing both would be
    // redundant, so ForgotPassword.tsx deliberately suppresses the latter
    // whenever a dev link is available (see its `!devToken` guard). Either
    // way the user always gets *some* real, honest next step - that's
    // what this test checks, not which exact one.
    await page.goto("/forgot-password");
    await page.getByLabel(/email/i).fill(uniqueEmail);
    await page.getByRole("button", { name: /send reset link/i }).click();
    await expect(page.getByText(/reset link has been generated/i)).toBeVisible({ timeout: 10_000 });
    const devLink = page.getByRole("link", { name: /use this reset link/i });
    const uncertainNote = page.getByText(/could not confirm email delivery/i);
    await expect(devLink.or(uncertainNote)).toBeVisible();
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

// These tests need a Super Administrator account - `python -m
// scripts.seed_demo_accounts` (refuses to run outside ENVIRONMENT=production)
// creates admin.demo@example.com / AdminDemo123!, see .github/workflows/ci.yml's
// e2e-tests job. Running this file locally without seeding first will fail
// only this describe block - the rest of the suite doesn't need it.
test.describe("admin verification workflows", () => {
  const ADMIN_EMAIL = "admin.demo@example.com";
  const ADMIN_PASSWORD = "AdminDemo123!";

  async function loginAsAdmin(page: import("@playwright/test").Page) {
    // Staff logins now stop for an emailed 2FA code (see OTP_LOGIN_ROLES in
    // routers/auth.py) - DEV_EXPOSE_OTP is on in CI, so the code is shown
    // directly on the page instead of needing a real inbox, same pattern as
    // the signup OTP step used elsewhere in this file.
    await page.goto("/login");
    await page.getByLabel(/^email/i).fill(ADMIN_EMAIL);
    await page.getByLabel(/^password/i).fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    const devCode = page.getByText(/your code is/i);
    await expect(devCode).toBeVisible({ timeout: 10_000 });
    const code = (await devCode.textContent())?.match(/(\d{6})/)?.[1];
    await page.getByLabel(/verification code/i).fill(code!);
    await page.getByRole("button", { name: /verify and sign in/i }).click();
    await expect(page).toHaveURL(/\/staff/, { timeout: 10_000 });
  }

  test("farmer submits a rating, staff approves it, and it appears on the public product page", async ({ page, request, baseURL }) => {
    // Product creation/publication isn't exercised through the UI
    // elsewhere in this suite - drive it directly via the API (same
    // approach the backend's own pytest suite uses) so this test can
    // focus on the review lifecycle itself.
    const adminLogin = await request.post(`${baseURL}/api/v1/auth/login`, { data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD } });
    expect(adminLogin.ok()).toBeTruthy();
    const otpBody = await adminLogin.json();
    expect(otpBody.otp_required).toBeTruthy();
    const admin = await request.post(`${baseURL}/api/v1/auth/login/verify-otp`, { data: { email: ADMIN_EMAIL, code: otpBody.dev_otp_code } });
    expect(admin.ok()).toBeTruthy();
    const csrf = admin.headers()["x-csrf-token"];
    const suffix = Date.now();
    const product = await request.post(`${baseURL}/api/v1/products`, {
      headers: { "x-csrf-token": csrf },
      data: { sku: `SKU-E2E-${suffix}`, name: "E2E Reviewed Product", slug: `e2e-reviewed-${suffix}`, precautions: "x", full_description: "x" },
    });
    expect(product.ok()).toBeTruthy();
    const productId = (await product.json()).id;
    const category = await request.post(`${baseURL}/api/v1/categories`, { headers: { "x-csrf-token": csrf }, data: { name: `E2E Cat ${suffix}`, slug: `e2e-cat-${suffix}` } });
    expect(category.ok()).toBeTruthy();
    const categoryId = (await category.json()).id;
    const updated = await request.put(`${baseURL}/api/v1/products/${productId}`, {
      headers: { "x-csrf-token": csrf },
      data: { sku: `SKU-E2E-${suffix}`, name: "E2E Reviewed Product", slug: `e2e-reviewed-${suffix}`, category_id: categoryId, precautions: "x", full_description: "x" },
    });
    expect(updated.ok()).toBeTruthy();
    for (const status of ["in_review", "approved", "published"]) {
      const transition = await request.post(`${baseURL}/api/v1/products/${productId}/transition/${status}`, { headers: { "x-csrf-token": csrf }, data: {} });
      expect(transition.ok()).toBeTruthy();
    }
    await request.post(`${baseURL}/api/v1/auth/logout`, { headers: { "x-csrf-token": csrf } });

    // Farmer signs up (fresh browser session) and submits a rating. The
    // name is suffixed so repeated local test runs (which each leave a
    // pending review behind if a later step fails) never collide when
    // scoping locators to "this run's" review below.
    const reviewerName = `Playwright Reviewer ${suffix}`;
    await page.goto("/signup");
    await page.getByLabel(/full name/i).fill(reviewerName);
    await page.getByLabel(/^email/i).fill(`e2e-reviewer-${suffix}@example.com`);
    await page.getByLabel(/phone/i).fill("9876543217");
    await page.getByLabel(/^password/i).fill("CorrectHorseBattery9!");
    await page.getByRole("button", { name: /send verification code/i }).click();
    const devCode = page.getByText(/your code is/i);
    await expect(devCode).toBeVisible({ timeout: 10_000 });
    const code = (await devCode.textContent())?.match(/(\d{6})/)?.[1];
    await page.getByLabel(/verification code/i).fill(code!);
    await page.getByRole("button", { name: /verify and create account/i }).click();
    await expect(page).toHaveURL(/\/farmer/, { timeout: 10_000 });

    await page.goto(`/products/e2e-reviewed-${suffix}`);
    await expect(page.getByText(/no farmer reviews are available yet/i)).toBeVisible();
    await page.getByLabel(/rating/i).selectOption("5");
    await page.getByRole("button", { name: /submit rating/i }).click();
    await expect(page.getByText(/thank you/i)).toBeVisible({ timeout: 10_000 });

    // Staff logs in, sees it pending, approves it.
    await loginAsAdmin(page);
    await page.goto("/staff/reviews");
    const reviewCard = page.getByText(reviewerName).locator("..").locator("..");
    await expect(reviewCard.getByRole("button", { name: /^approve$/i })).toBeVisible({ timeout: 10_000 });
    await reviewCard.getByRole("button", { name: /^approve$/i }).click();
    await expect(page.getByText(reviewerName)).toHaveCount(0, { timeout: 10_000 });

    // Public product page now shows it.
    await page.goto(`/products/e2e-reviewed-${suffix}`);
    await expect(page.getByText(/5\.0 average from 1 verified farmer review/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(reviewerName)).toBeVisible();
  });

  test("staff can verify, approve, and publish a certificate through the full workflow", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/staff/documents");

    const suffix = Date.now();
    await page.getByLabel(/title/i).fill(`E2E Certificate ${suffix}`);
    await page.setInputFiles("#doc-file", { name: "cert.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 e2e test certificate") });
    await page.getByRole("button", { name: /^upload$/i }).click();
    await expect(page.getByText(`E2E Certificate ${suffix}`)).toBeVisible({ timeout: 10_000 });

    const row = page.getByRole("row").filter({ hasText: `E2E Certificate ${suffix}` });
    await row.getByRole("button", { name: /^verify$/i }).click();
    await expect(row.getByRole("button", { name: /^approve$/i })).toBeVisible({ timeout: 10_000 });
    await row.getByRole("button", { name: /^approve$/i }).click();
    await expect(row.getByRole("button", { name: /^publish$/i })).toBeVisible({ timeout: 10_000 });
    await row.getByRole("button", { name: /^publish$/i }).click();
    await expect(row.getByRole("button", { name: /^unpublish$/i })).toBeVisible({ timeout: 10_000 });

    await page.goto("/certificates");
    await expect(page.getByText(`E2E Certificate ${suffix}`)).toBeVisible({ timeout: 10_000 });
  });

  test("a farmer is blocked from the staff dashboard", async ({ page }) => {
    const suffix = Date.now();
    await page.goto("/register");
    await page.getByLabel(/full name/i).fill("E2E Unauthorized Farmer");
    await page.getByLabel(/^email/i).fill(`e2e-unauth-${suffix}@example.com`);
    await page.getByLabel(/phone/i).fill("9876543218");
    await page.getByLabel(/^password/i).fill("CorrectHorseBattery9!");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/farmer/, { timeout: 10_000 });

    await page.goto("/staff");
    await expect(page).toHaveURL(/\/403/, { timeout: 10_000 });
  });
});
