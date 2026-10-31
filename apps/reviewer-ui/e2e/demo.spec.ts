import { expect, test } from "@playwright/test";

test("a first-time reviewer can save a note and see it after a reload", async ({ page }, testInfo) => {
  await page.goto("/#workspace");
  await expect(page.getByText("API 0.62.1", { exact: true })).toBeAttached();
  await page.getByRole("navigation", { name: "Reviewer console sections" })
    .getByRole("button", { name: /Exceptions/ }).click();
  await expect(page.getByRole("heading", { name: "Exception desk", exact: true })).toBeVisible();
  await expect(page.getByRole("list", { name: "Exceptions", exact: true }).getByRole("button")).toHaveCount(9);
  const note = `Asked the synthetic source owner for the missing ID (${testInfo.project.name}).`;
  await page.getByLabel("Resolution note", { exact: true }).fill(note);
  await page.getByRole("button", { name: "Save resolution", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Resolution saved" })).toBeVisible();
  await page.reload();
  await page.getByRole("navigation", { name: "Reviewer console sections" })
    .getByRole("button", { name: /Exceptions/ }).click();
  const history = page.getByRole("region", { name: "Resolution history", exact: true });
  await expect(history.getByText(note, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator("#workspace").screenshot({ path: testInfo.outputPath("connected-demo.png") });
});

test("the demo viewer cannot submit exception resolutions", async ({ page }) => {
  await page.goto("/#workspace");
  await expect(page.getByText("API 0.62.1", { exact: true })).toBeAttached();
  await page.getByRole("navigation", { name: "Reviewer console sections" })
    .getByRole("button", { name: /Exceptions/ }).click();
  await page.getByRole("combobox", { name: "Local demo identity", exact: true }).selectOption("demo-viewer");
  await expect(page.getByText("Your account cannot review exceptions.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save resolution", exact: true })).toHaveCount(0);
});

test("protects unfinished notes and restores safe filters on return", async ({ page }, testInfo) => {
  await page.goto("/#workspace");
  await expect(page.getByText("API 0.62.1", { exact: true })).toBeAttached();
  const navigation = page.getByRole("navigation", { name: "Reviewer console sections" });
  await navigation.getByRole("button", { name: /Exceptions/ }).click();
  await page.getByRole("combobox", { name: "Exception filter", exact: true }).selectOption("all");
  await page.getByRole("combobox", { name: "Severity", exact: true }).selectOption("blocking");
  await page.getByRole("combobox", { name: "Sort order", exact: true }).selectOption("newest");
  await expect(page.getByText("Showing 1-9 of 9 matching issues", { exact: true })).toBeVisible();
  const draft = "Unfinished source-owner review";
  await page.getByLabel("Resolution note", { exact: true }).fill(draft);
  page.once("dialog", dialog => dialog.dismiss());
  await navigation.getByRole("button", { name: /Case overview/ }).click();
  await expect(page.getByLabel("Resolution note", { exact: true })).toHaveValue(draft);
  page.once("dialog", dialog => dialog.dismiss());
  await page.getByRole("list", { name: "Exceptions", exact: true }).getByRole("button").nth(1).click();
  await expect(page.getByLabel("Resolution note", { exact: true })).toHaveValue(draft);
  page.once("dialog", dialog => dialog.accept());
  await navigation.getByRole("button", { name: /Case overview/ }).click();
  await navigation.getByRole("button", { name: /Exceptions/ }).click();
  await expect(page.getByRole("combobox", { name: "Sort order", exact: true })).toHaveValue("newest");
  await expect(page.getByRole("combobox", { name: "Severity", exact: true })).toHaveValue("blocking");
  await expect(page.getByLabel("Resolution note", { exact: true })).toHaveValue("");
  await page.reload();
  await navigation.getByRole("button", { name: /Exceptions/ }).click();
  await expect(page.getByRole("combobox", { name: "Sort order", exact: true })).toHaveValue("newest");
  await page.getByRole("combobox", { name: "Severity", exact: true }).selectOption("warning");
  await expect(page.getByText("Showing 0-0 of 0 matching issues", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Next page", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Reset filters", exact: true }).click();
  await expect(page.getByText("Showing 1-9 of 9 matching issues", { exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Sort order", exact: true })).toHaveValue("oldest");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator("#workspace").screenshot({ path: testInfo.outputPath("reviewer-workflow.png") });
});

test("warns before a document navigation discards an unfinished note", async ({ page }) => {
  await page.goto("/#workspace");
  await expect(page.getByText("API 0.62.1", { exact: true })).toBeAttached();
  await page.getByRole("navigation", { name: "Reviewer console sections" })
    .getByRole("button", { name: /Exceptions/ }).click();
  await page.getByLabel("Resolution note", { exact: true }).fill("Keep this unfinished note");
  let prompted = false;
  page.once("dialog", async dialog => {
    expect(dialog.type()).toBe("beforeunload");
    prompted = true;
    await dialog.dismiss();
  });
  await page.getByRole("link", { name: "Browse documentation", exact: true }).click();
  expect(prompted).toBe(true);
  await expect(page.getByLabel("Resolution note", { exact: true })).toHaveValue("Keep this unfinished note");
});
