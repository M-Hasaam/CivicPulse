import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";

type Theme = "light" | "dark" | "system";
function storedTheme(): Theme {
  try {
    const value = localStorage.getItem("civicpulse-theme");
    if (value === "light" || value === "dark") return value;
  } catch {
    /* Storage can be unavailable in private browsing. */
  }
  return "system";
}
export function ThemePicker() {
  const [theme, setTheme] = useState<Theme>(storedTheme);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme =
        theme === "system" ? (media.matches ? "dark" : "light") : theme;
    };
    apply();
    try {
      localStorage.setItem("civicpulse-theme", theme);
    } catch {
      /* Keep the preference for this session. */
    }
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  return (
    <div className="theme-picker" role="group" aria-label="Colour theme">
      {(
        [
          { value: "light", Icon: Sun },
          { value: "dark", Icon: Moon },
          { value: "system", Icon: Monitor },
        ] as const
      ).map(({ value, Icon }) => (
        <button
          key={value}
          type="button"
          aria-label={`${value[0].toUpperCase()}${value.slice(1)} theme`}
          title={`${value[0].toUpperCase()}${value.slice(1)} theme`}
          aria-pressed={theme === value}
          onClick={() => setTheme(value)}
        >
          <Icon size={16} />
        </button>
      ))}
    </div>
  );
}
