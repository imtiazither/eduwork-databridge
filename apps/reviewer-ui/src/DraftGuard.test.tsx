import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useLayoutEffect, useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { DraftGuardProvider, useDraftGuard } from "./DraftGuard";

function Harness({ busy = false }: { busy?: boolean }) {
  const guard = useDraftGuard();
  const [left, setLeft] = useState(false);
  useLayoutEffect(() => { guard.update({ dirty: true, busy, discard: () => {} }); }, [guard.update, busy]);
  return <button onClick={() => guard.leave(() => setLeft(true))}>{left ? "Left desk" : "Leave desk"}</button>;
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

test("keeps the desk open when leaving with a draft is cancelled", () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<DraftGuardProvider><Harness /></DraftGuardProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Leave desk" }));
  expect(screen.queryByText("Left desk")).not.toBeInTheDocument();
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Leave desk" }));
  expect(screen.getByText("Left desk")).toBeInTheDocument();
});

test("cannot leave while a resolution request is pending", () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<DraftGuardProvider><Harness busy /></DraftGuardProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Leave desk" }));
  expect(screen.queryByText("Left desk")).not.toBeInTheDocument();
  expect(confirm).not.toHaveBeenCalled();
});
