const THEME_INIT_SCRIPT = `
(() => {
  const storageKey = "app-theme";
  const root = document.documentElement;
  const savedTheme = window.localStorage.getItem(storageKey);
  const nextTheme = savedTheme === "light" || savedTheme === "dark" || savedTheme === "system"
    ? savedTheme
    : "light";
  root.setAttribute("data-theme", nextTheme);
})();
`;

export default function ThemeInitScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />;
}
