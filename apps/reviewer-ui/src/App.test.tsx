import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { fallbackSummary } from "./demoData";

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

function mockSuccessfulApi() {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith("/api/v1/version")
      ? { version: "0.14.0", maturity: "release-candidate", completed_phases: Array.from({ length: 15 }, (_, index) => index) }
      : fallbackSummary;
    return Promise.resolve({ ok: true, json: async () => body } as Response);
  }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("renders the case story and live API version", async () => {
  mockSuccessfulApi();
  renderApp();
  expect(screen.getByRole("heading", { name: "Can we trust the training report?" })).toBeInTheDocument();
  expect(await screen.findByText("API 0.14.0")).toBeInTheDocument();
  expect(screen.getByText("366")).toBeInTheDocument();
});

test("keeps a useful synthetic preview when the API is offline", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  renderApp();
  expect(await screen.findByText("Preview data")).toBeInTheDocument();
  expect(screen.getAllByText("43").length).toBeGreaterThan(0);
  expect(screen.getByText(/Not a customer outcome/)).toBeInTheDocument();
});

test("lets a reviewer inspect exceptions", async () => {
  mockSuccessfulApi();
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: /Exceptions/ }));
  expect(screen.getByRole("heading", { name: /short queue with reasons/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Unknown completion status/ }));
  expect(screen.getByRole("heading", { name: /Hiro Johnson/ })).toBeInTheDocument();
});

test("makes the identity decision a reversible preview", () => {
  mockSuccessfulApi();
  renderApp();
  fireEvent.click(screen.getByRole("button", { name: /Identity review/ }));
  fireEvent.click(screen.getByRole("button", { name: "Keep separate" }));
  expect(screen.getAllByText("Keep separate").length).toBeGreaterThan(0);
  expect(screen.getByText(/resets on refresh/)).toBeInTheDocument();
});

test("connects the product story to the public resources", () => {
  mockSuccessfulApi();
  renderApp();
  expect(
    screen.getByRole("heading", { name: /answer spread across four systems/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open the field guide/i })).toHaveAttribute(
    "href",
    "/docs/EduWork_DataBridge_Field_Guide.pdf",
  );
  expect(screen.getAllByRole("link", { name: /Documentation/i })[0]).toHaveAttribute(
    "href",
    "/docs/",
  );
});
