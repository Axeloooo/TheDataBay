import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { ensurePersistFormat } from "@/stores/persist-utils";

export type Theme = "dark" | "light" | "system";

type ThemePersistedState = {
  theme: Theme;
};

type ThemeStore = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  applyTheme: (theme: Theme) => void;
};

const STORAGE_KEY = "vite-ui-theme";

function normalizeTheme(raw: string): Theme {
  switch (raw.trim()) {
    case "light":
    case "dark":
    case "system":
      return raw.trim() as Theme;
    default:
      return "system";
  }
}

ensurePersistFormat<ThemePersistedState>(STORAGE_KEY, (raw) => ({
  theme: normalizeTheme(raw),
}));

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: "system",
      setTheme: (theme) => set({ theme }),
      applyTheme: (theme) => {
        const root = window.document.documentElement;
        root.classList.remove("light", "dark");

        if (theme === "system") {
          const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
            .matches
            ? "dark"
            : "light";
          root.classList.add(systemTheme);
          return;
        }

        root.classList.add(theme);
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
      }),
    },
  ),
);
