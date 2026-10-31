import { afterEach, expect, test, vi } from "vitest";
import { defaultExceptionPreferences, readExceptionPreferences, writeExceptionPreferences } from "./exceptionPreferences";

afterEach(() => { vi.restoreAllMocks(); window.sessionStorage.clear(); });

test("keeps preferences separate by identity and organization", () => {
  const selected = { filter: "closed", severity: "warning", sort: "severity" };
  writeExceptionPreferences("user-a", "org-a", selected);
  expect(readExceptionPreferences("user-a", "org-a")).toEqual(selected);
  expect(readExceptionPreferences("user-b", "org-a")).toEqual(defaultExceptionPreferences);
  expect(readExceptionPreferences("user-a", "org-b")).toEqual(defaultExceptionPreferences);
});

test.each(["not-json", "null", "[]", '{"filter":"__proto__","severity":"invalid","sort":"unknown"}'])("ignores invalid stored preferences: %s", value => {
  vi.spyOn(Storage.prototype, "getItem").mockReturnValue(value);
  expect(readExceptionPreferences("u", "o")).toEqual(defaultExceptionPreferences);
});

test("handles blocked storage without preventing reviews", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(readExceptionPreferences("u", "o")).toEqual(defaultExceptionPreferences);
  expect(() => writeExceptionPreferences("u", "o", defaultExceptionPreferences)).not.toThrow();
});

test("writes only allowed preference fields, never notes or search", () => {
  writeExceptionPreferences("u", "o", { ...defaultExceptionPreferences, note: "Private draft", q: "Learner name" } as typeof defaultExceptionPreferences);
  const value = window.sessionStorage.getItem(window.sessionStorage.key(0)!);
  expect(JSON.parse(value!)).toEqual(defaultExceptionPreferences);
});
