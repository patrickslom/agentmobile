"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BookMarked,
  FolderKanban,
  HeartPulse,
  LogOut,
  Menu,
  MessageSquareText,
  PanelLeftClose,
  Settings2,
  ShieldUser,
  X,
  type LucideIcon,
} from "lucide-react";
import WinkingLogo from "@/app/components/winking-logo";
import { ProtectedShellContextProvider } from "@/components/app/protected-shell-context";

const DESKTOP_SIDEBAR_OPEN_WIDTH = 300;
const DESKTOP_SIDEBAR_COLLAPSED_WIDTH = 84;
const SIDEBAR_COLLAPSED_STORAGE_KEY = "agentmobile_sidebar_collapsed";

type ProtectedShellProps = {
  isAdmin: boolean;
  children: React.ReactNode;
};

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

function navItems(isAdmin: boolean): NavItem[] {
  const items: NavItem[] = [
    { href: "/chat", label: "Chat", icon: MessageSquareText },
    { href: "/bookmarks", label: "Bookmarks", icon: BookMarked },
    { href: "/projects", label: "Projects", icon: FolderKanban },
    { href: "/heartbeats", label: "Heartbeats", icon: HeartPulse },
    { href: "/settings", label: "Settings", icon: Settings2 },
  ];

  if (isAdmin) {
    items.push({ href: "/admin", label: "Admin", icon: ShieldUser });
  }

  return items;
}

function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function SidebarNav({
  pathname,
  items,
  collapsed,
  mobile,
  onNavigate,
}: Readonly<{
  pathname: string;
  items: NavItem[];
  collapsed: boolean;
  mobile: boolean;
  onNavigate?: () => void;
}>) {
  return (
    <nav className="flex flex-col gap-2">
      {items.map((item) => {
        const Icon = item.icon;
        const active = isActivePath(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`group inline-flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm font-medium transition ${
              active
                ? "border-foreground bg-foreground text-background shadow-sm"
                : "border-border/70 bg-background/80 text-foreground hover:border-foreground/30 hover:bg-background"
            } ${collapsed && !mobile ? "justify-center px-0" : ""}`}
            title={collapsed && !mobile ? item.label : undefined}
          >
            <Icon className="h-5 w-5 shrink-0" />
            {collapsed && !mobile ? null : <span className="truncate">{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarFrame({
  pathname,
  items,
  collapsed,
  mobile,
  onClose,
  onToggleCollapsed,
}: Readonly<{
  pathname: string;
  items: NavItem[];
  collapsed: boolean;
  mobile: boolean;
  onClose?: () => void;
  onToggleCollapsed?: () => void;
}>) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-[linear-gradient(180deg,rgba(255,255,255,0.97)_0%,rgba(245,245,244,0.96)_100%)] text-foreground dark:bg-[linear-gradient(180deg,rgba(15,15,15,0.98)_0%,rgba(8,8,8,0.98)_100%)]">
      <div className={`shrink-0 border-b border-border/80 ${collapsed && !mobile ? "px-3 py-4" : "px-5 py-5"}`}>
        <div className={`flex items-center ${collapsed && !mobile ? "justify-center" : "justify-between"} gap-3`}>
          {collapsed && !mobile && onToggleCollapsed ? (
            <button
              type="button"
              aria-label="Expand sidebar"
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl transition hover:opacity-80"
              onClick={onToggleCollapsed}
            >
              <WinkingLogo size={30} />
            </button>
          ) : (
            <Link
              href="/chat"
              onClick={onClose}
              className="inline-flex items-center gap-3"
              title="AGENTMOBILE"
            >
              <WinkingLogo size={32} />
              <p className="text-sm font-semibold tracking-[0.24em] uppercase">AGENTMOBILE</p>
            </Link>
          )}

          {mobile ? (
            <button
              type="button"
              aria-label="Close navigation"
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border bg-background/90 transition hover:bg-background"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </button>
          ) : onToggleCollapsed && !collapsed ? (
            <button
              type="button"
              aria-label="Collapse sidebar"
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl text-muted-foreground transition hover:bg-background/60 hover:text-foreground"
              onClick={onToggleCollapsed}
            >
              <PanelLeftClose className="h-5 w-5" />
            </button>
          ) : null}
        </div>
      </div>

      <div className={`min-h-0 flex-1 overflow-y-auto ${collapsed && !mobile ? "px-3 py-4" : "px-4 py-5"}`}>
        <SidebarNav
          pathname={pathname}
          items={items}
          collapsed={collapsed}
          mobile={mobile}
          onNavigate={mobile ? onClose : undefined}
        />
      </div>

      <div
        className={`sticky bottom-0 z-10 mt-auto shrink-0 border-t border-border/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(245,245,244,0.98)_100%)] dark:bg-[linear-gradient(180deg,rgba(15,15,15,0.99)_0%,rgba(8,8,8,0.99)_100%)] ${collapsed && !mobile ? "px-3 py-4" : "px-4 py-5"}`}
      >
        <form method="post" action="/logout">
          <button
            type="submit"
            className={`inline-flex w-full items-center gap-3 rounded-2xl border border-border bg-background/90 py-3 text-sm font-medium transition hover:bg-background ${
              collapsed && !mobile ? "justify-center px-0" : "px-3"
            }`}
            title={collapsed && !mobile ? "Log out" : undefined}
          >
            <LogOut className="h-5 w-5 shrink-0" />
            {collapsed && !mobile ? null : <span>Log out</span>}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function ProtectedShell({ isAdmin, children }: ProtectedShellProps) {
  const pathname = usePathname();
  const [isMobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const items = useMemo(() => navItems(isAdmin), [isAdmin]);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY);
      setSidebarCollapsed(saved === "1");
    } catch {
      setSidebarCollapsed(false);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        SIDEBAR_COLLAPSED_STORAGE_KEY,
        sidebarCollapsed ? "1" : "0",
      );
    } catch {
      // Ignore localStorage write failures.
    }
  }, [sidebarCollapsed]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  return (
    <ProtectedShellContextProvider value={{ sidebarCollapsed }}>
      <div
        className="min-h-screen min-h-dvh w-full overflow-x-hidden bg-[radial-gradient(circle_at_top_left,rgba(0,0,0,0.045),transparent_28%),linear-gradient(180deg,#fcfcfb_0%,#f3f1eb_100%)] text-foreground md:flex dark:bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.05),transparent_24%),linear-gradient(180deg,#111111_0%,#080808_100%)]"
      >
        <aside className="hidden border-r border-border/80 bg-transparent md:fixed md:inset-y-0 md:left-0 md:z-20 md:flex md:h-screen md:min-h-screen md:flex-col">
          <SidebarFrame
            pathname={pathname}
            items={items}
            collapsed={sidebarCollapsed}
            mobile={false}
            onToggleCollapsed={() => setSidebarCollapsed((current) => !current)}
          />
        </aside>

        <div
          className="hidden md:block md:shrink-0"
          style={{
            width: sidebarCollapsed
              ? DESKTOP_SIDEBAR_COLLAPSED_WIDTH
              : DESKTOP_SIDEBAR_OPEN_WIDTH,
          }}
          aria-hidden
        />

        <div className="min-w-0 flex-1 overflow-x-hidden">
          <header className="sticky top-0 z-30 border-b border-border/80 bg-background/92 px-4 py-3 backdrop-blur md:hidden">
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                aria-label="Open navigation"
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-border bg-background transition hover:bg-muted"
                onClick={() => setMobileNavOpen(true)}
              >
                <Menu className="h-5 w-5" />
              </button>
              <Link href="/chat" className="inline-flex items-center gap-3">
                <WinkingLogo size={28} />
                <span className="text-sm font-semibold tracking-[0.22em] uppercase">AGENTMOBILE</span>
              </Link>
              <span className="h-11 w-11" aria-hidden />
            </div>
          </header>

          {isMobileNavOpen ? (
            <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true">
              <button
                type="button"
                aria-label="Close navigation"
                className="absolute inset-0 bg-black/55"
                onClick={() => setMobileNavOpen(false)}
              />
              <aside className="relative z-10 h-full w-full border-r border-border bg-background">
                <SidebarFrame
                  pathname={pathname}
                  items={items}
                  collapsed={false}
                  mobile
                  onClose={() => setMobileNavOpen(false)}
                />
              </aside>
            </div>
          ) : null}

          <main className="min-w-0 overflow-x-hidden px-4 py-5 sm:px-6 sm:py-6 md:px-8 md:py-8">
            {children}
          </main>
        </div>
      </div>
    </ProtectedShellContextProvider>
  );
}
