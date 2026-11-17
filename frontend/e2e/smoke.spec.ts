import { test, expect, type Page } from "@playwright/test";

// One end-to-end round trip through the real app:
// pick a model manually, send a message, switch model, send again, then
// delete the conversation.

async function openSidebarOnMobile(page: Page) {
  const openButton = page.getByRole("button", { name: "Open sidebar" });
  if (await openButton.isVisible()) {
    await openButton.click();
  }
}

async function closeSidebarOnMobile(page: Page) {
  const closeButton = page.getByRole("button", { name: "Close sidebar" });
  if (await closeButton.isVisible()) {
    await closeButton.click();
  }
}

async function selectOption(page: Page, selectName: string, optionName: string) {
  // Composer controls only: message-level controls (e.g. "Switch model") can
  // share a word with the composer's labels.
  await page.locator("form").getByRole("button", { name: selectName, exact: true }).click();
  await page.getByRole("option", { name: optionName, exact: true }).click();
}

async function sendMessage(page: Page, text: string) {
  await page.getByLabel("Message input").fill(text);
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText(`Mock reply from ${text}`)).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop generating" })).toHaveCount(0);
}

test("chat round trip with the mock provider", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Message input")).toBeVisible();

  await selectOption(page, "Routing mode", "Manual Select");
  await selectOption(page, "Provider", "mock");
  await selectOption(page, "Model", "Mock Model");

  const routeLabels = (model: string) =>
    page.getByRole("main").getByText(model, { exact: true });

  await sendMessage(page, "Hello from the smoke test");
  await expect(routeLabels("mock-model")).toHaveCount(1);
  await expect(page.getByText("11 in · 7 out")).toBeVisible();

  // Editing the question replaces the answer that followed it.
  await page.getByRole("main").getByText("Hello from the smoke test", { exact: true }).hover();
  await page.getByRole("button", { name: "Edit message" }).click();
  await page.getByLabel("Edit message text").fill("Edited smoke message");
  await page.getByRole("button", { name: "Save and resend" }).click();
  await expect(page.getByText("Mock reply from Edited smoke message")).toBeVisible();
  await expect(page.getByText("Mock reply from Hello from the smoke test")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Stop generating" })).toHaveCount(0);

  // The answer's model switch re-runs it with the chosen model and visibly
  // moves the composer to Manual with that model.
  await page.getByRole("button", { name: "Select: Switch model" }).click();
  await page.getByRole("option", { name: "Mock Model Pro · mock", exact: true }).click();
  await expect(routeLabels("mock-model-pro")).toHaveCount(1);
  await expect(routeLabels("mock-model")).toHaveCount(0);
  await expect(page.locator("form")).toContainText("Mock Model Pro");

  await expect.poll(() => page.locator("form").evaluate(form => {
    const bounds = form.getBoundingClientRect();
    return Array.from(form.querySelectorAll("button")).every(button => {
      const rect = button.getBoundingClientRect();
      return rect.left >= bounds.left && rect.right <= bounds.right;
    });
  })).toBe(true);
  await sendMessage(page, "Second smoke message");
  // The switch re-ran the edited answer with Mock Model Pro, so both answers
  // now carry the pro model id.
  await expect(routeLabels("mock-model-pro")).toHaveCount(2);

  const fitsViewport = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth
  );
  expect(fitsViewport).toBe(true);

  await openSidebarOnMobile(page);
  const sidebar = page.getByRole("navigation", { name: "Sidebar navigation" });
  const currentRow = sidebar
    .locator('[role="listitem"]')
    .filter({ has: page.locator('[aria-current="page"]') });
  await expect(currentRow).toHaveCount(1);

  await currentRow.hover();
  page.once("dialog", (dialog) => dialog.accept());
  await currentRow.getByRole("button", { name: /^Delete/ }).click();

  await expect(page.getByText("Conversation deleted")).toBeVisible();
  await expect(currentRow).toHaveCount(0);

  await closeSidebarOnMobile(page);
  await expect(page.getByText("Good afternoon.")).toBeVisible();
});
