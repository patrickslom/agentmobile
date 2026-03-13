"use client";

import { FolderKanban, Sparkles } from "lucide-react";

export default function ProjectsPlaceholderPageClient() {
  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="rounded-[28px] border border-border/80 bg-background/92 p-6 shadow-[0_12px_40px_rgba(0,0,0,0.05)] backdrop-blur sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
          Projects
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Projects are coming soon.
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground sm:text-base">
          This module is reserved for future project organization work. The route and shell placement are ready so the product structure does not need to change later.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-[24px] border border-border bg-background/88 p-6">
          <FolderKanban className="h-7 w-7 text-foreground" />
          <h2 className="mt-4 text-xl font-semibold tracking-tight">Workspace hub</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Future project browsing, selection, and metadata management will live here.
          </p>
        </section>
        <section className="rounded-[24px] border border-border bg-background/88 p-6">
          <Sparkles className="h-7 w-7 text-foreground" />
          <h2 className="mt-4 text-xl font-semibold tracking-tight">Designed to expand</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            The page is intentionally lightweight for now so later project features can be added without another navigation refactor.
          </p>
        </section>
      </div>
    </section>
  );
}
