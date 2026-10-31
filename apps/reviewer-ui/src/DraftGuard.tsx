import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

interface Draft {
  dirty: boolean;
  busy: boolean;
  discard: () => void;
}
const cleanDraft: Draft = { dirty: false, busy: false, discard: () => {} };
const DraftContext = createContext<{
  active: boolean;
  update: (draft: Draft) => void;
  leave: (action: () => void) => void;
} | null>(null);

export function DraftGuardProvider({ children }: { children: ReactNode }) {
  const draft = useRef(cleanDraft);
  const [active, setActive] = useState(false);
  const update = useCallback((next: Draft) => {
    draft.current = next;
    setActive(next.dirty || next.busy);
  }, []);
  const leave = useCallback((action: () => void) => {
    if (draft.current.busy) return;
    if (draft.current.dirty && !window.confirm("Discard unsaved resolution changes?")) return;
    draft.current.discard();
    action();
  }, []);
  useEffect(() => {
    if (!active) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = true; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [active]);
  return <DraftContext.Provider value={{ active, update, leave }}>{children}</DraftContext.Provider>;
}

export function useDraftGuard() {
  const guard = useContext(DraftContext);
  if (!guard) throw new Error("DraftGuardProvider is required");
  return guard;
}
