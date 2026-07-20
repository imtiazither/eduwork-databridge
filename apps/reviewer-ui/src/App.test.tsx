import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { App } from "./App";

test("renders the blueprint-complete boundary", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ version: "0.14.0", maturity: "release-candidate", completed_phases: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] }),
  }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
  expect(screen.getByRole("heading", { name: "EduWork DataBridge" })).toBeInTheDocument();
  expect(await screen.findByText(/Version 0.14.0/)).toBeInTheDocument();
});
