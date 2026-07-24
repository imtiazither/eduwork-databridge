(() => {
  const storageKey = "eduwork-databridge-theme";

  const syncTheme = () => {
    const theme = document.body.dataset.mdColorScheme === "slate" ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#110e06" : "#f8f4eb");

    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {
      // Theme switching remains available when storage is blocked.
    }

    document.querySelectorAll(".databridge-theme-toggle").forEach((toggle) => {
      const dark = theme === "dark";
      toggle.setAttribute("aria-pressed", String(dark));
      toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
      const label = toggle.querySelector(".databridge-theme-toggle-label");
      if (label) label.textContent = dark ? "Light" : "Dark";
    });
  };

  const setTheme = (theme) => {
    const scheme = theme === "dark" ? "slate" : "default";
    document.body.dataset.mdColorScheme = scheme;
    document.body.dataset.mdColorPrimary = "custom";
    document.body.dataset.mdColorAccent = "custom";

    const input = document.querySelector(
      `[name="__palette"][data-md-color-scheme="${scheme}"]`,
    );
    if (input instanceof HTMLInputElement) input.checked = true;

    if (typeof window.__md_set === "function") {
      window.__md_set("__palette", {
        color: {
          media: "",
          scheme,
          primary: "custom",
          accent: "custom",
        },
      });
    }
    syncTheme();
  };

  const bindThemeToggles = () => {
    document.querySelectorAll(".databridge-theme-toggle").forEach((toggle) => {
      if (toggle.dataset.themeBound === "true") return;
      toggle.dataset.themeBound = "true";
      toggle.addEventListener("click", () => {
        const targetTheme =
          document.body.dataset.mdColorScheme === "slate" ? "light" : "dark";
        setTheme(targetTheme);
      });
    });
    syncTheme();
  };

  const observer = new MutationObserver(syncTheme);
  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });

  if (window.document$) {
    window.document$.subscribe(bindThemeToggles);
  } else {
    bindThemeToggles();
  }
})();
