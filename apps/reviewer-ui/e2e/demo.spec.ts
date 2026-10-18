import { expect, test } from "@playwright/test";

test("a first-time reviewer can save a note and see it after a reload", async ({ page }, testInfo) => {
  await page.goto("/#workspace");
  await expect(page.getByText("API 0.61.0", { exact: true })).toBeAttached();
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
  await expect(page.getByText("API 0.61.0", { exact: true })).toBeAttached();
  await page.getByRole("navigation", { name: "Reviewer console sections" })
    .getByRole("button", { name: /Exceptions/ }).click();
  await page.getByRole("combobox", { name: "Local demo identity", exact: true }).selectOption("demo-viewer");
  await expect(page.getByText("Your account cannot review exceptions.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save resolution", exact: true })).toHaveCount(0);
});
