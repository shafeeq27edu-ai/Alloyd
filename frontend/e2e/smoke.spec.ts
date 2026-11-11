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
  await page.getByRole("button", { name: selectName }).click();
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

  await sendMessage(page, "Hello from the smoke test");
  await expect(page.getByText("mock-model", { exact: true })).toBeVisible();

  await selectOption(page, "Model", "Mock Model Pro");
  await sendMessage(page, "Second smoke message");
  await expect(page.getByText("mock-model-pro", { exact: true })).toBeVisible();

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
