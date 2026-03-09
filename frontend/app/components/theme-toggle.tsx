"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "app-theme";
const THEMES = ["light", "dark", "system"] as const;

type ThemeName = (typeof THEMES)[number];

function isThemeName(value: string | null): value is ThemeName {
  return value === "light" || value === "dark" || value === "system";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeName>(() => {
    if (typeof window === "undefined") {
      return "light";
    }

    const savedTheme = window.localStorage.getItem(STORAGE_KEY);
    return isThemeName(savedTheme) ? savedTheme : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const onThemeChange = (nextTheme: ThemeName) => {
    document.documentElement.setAttribute("data-theme", nextTheme);
    window.localStorage.setItem(STORAGE_KEY, nextTheme);
    setTheme(nextTheme);
  };

  return (
    <div className="inline-flex rounded-lg border border-border bg-muted p-1">
      {THEMES.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onThemeChange(option)}
          className={`rounded-md px-2 py-1 text-xs font-medium capitalize transition ${
            theme === option
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-pressed={theme === option}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
