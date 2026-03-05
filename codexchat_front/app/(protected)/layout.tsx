import Link from "next/link";
import { redirect } from "next/navigation";
import ThemeToggle from "@/app/components/theme-toggle";
import { hasSessionCookie } from "@/lib/auth-session";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authenticated = await hasSessionCookie();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <div className="grid min-h-screen min-h-dvh w-full bg-background text-foreground md:grid-cols-[280px_1fr]">
      <aside className="border-b border-border bg-muted/50 p-4 md:border-r md:border-b-0 md:p-5">
        <div className="flex items-center justify-between md:justify-start">
          <Link href="/chat" className="text-sm font-semibold tracking-[0.18em] uppercase">
            CodexChat
          </Link>
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground md:hidden">
            Preview
          </span>
        </div>

        <button
          type="button"
          className="mt-4 w-full rounded-lg border border-border bg-background px-3 py-2 text-left text-sm font-medium transition hover:bg-muted"
        >
          + New chat
        </button>

        <div className="mt-6 space-y-2">
          <p className="text-xs font-semibold tracking-[0.16em] uppercase text-muted-foreground">
            Recent
          </p>
          <ul className="space-y-1">
            <li className="rounded-md border border-border bg-background px-3 py-2 text-sm">
              Deployment checklist review
            </li>
            <li className="rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
              MVP database schema planning
            </li>
            <li className="rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
              Frontend layout polish notes
            </li>
          </ul>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <nav className="flex items-center gap-3 text-sm text-muted-foreground">
              <Link href="/chat" className="rounded-md px-2 py-1 transition hover:bg-muted hover:text-foreground">
                Chat
              </Link>
              <Link
                href="/settings"
                className="rounded-md px-2 py-1 transition hover:bg-muted hover:text-foreground"
              >
                Settings
              </Link>
              <Link
                href="/settings/admin"
                className="rounded-md px-2 py-1 transition hover:bg-muted hover:text-foreground"
              >
                Admin
              </Link>
            </nav>

            <div className="flex items-center gap-2">
              <ThemeToggle />
              <form method="post" action="/logout">
                <button
                  type="submit"
                  className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium transition hover:bg-muted"
                >
                  Log out
                </button>
              </form>
            </div>
          </div>
        </header>

        <main className="px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
