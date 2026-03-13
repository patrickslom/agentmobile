"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, FolderKanban, FolderSearch, Plus, RefreshCcw, Save, Search } from "lucide-react";
import { useRouter } from "next/navigation";

type ProjectItem = {
  id: string;
  name: string;
  rootPath: string;
  indexMdPath: string | null;
  isActive: boolean;
  updatedAt: string;
};

type ProjectFormState = {
  name: string;
  rootPath: string;
  indexMdPath: string;
};

type DirectoryItem = {
  path: string;
  displayName: string;
};

type DirectoryPickerTarget =
  | { kind: "create" }
  | { kind: "edit"; projectId: string }
  | null;

const EMPTY_FORM: ProjectFormState = {
  name: "",
  rootPath: "",
  indexMdPath: "",
};

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const match = document.cookie.match(/(?:^|;\s*)agentmobile_csrf=([^;]+)/);
  if (!match?.[1]) {
    return null;
  }

  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

function withCsrfHeader(headers?: HeadersInit): HeadersInit | undefined {
  const token = readCsrfToken();
  if (!token) {
    return headers;
  }

  const next = new Headers(headers);
  next.set("x-csrf-token", token);
  return next;
}

function normalizeProject(raw: unknown): ProjectItem | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const item = raw as {
    id?: unknown;
    name?: unknown;
    root_path?: unknown;
    index_md_path?: unknown;
    is_active?: unknown;
    updated_at?: unknown;
  };

  if (
    typeof item.id !== "string" ||
    typeof item.name !== "string" ||
    typeof item.root_path !== "string"
  ) {
    return null;
  }

  return {
    id: item.id,
    name: item.name,
    rootPath: item.root_path,
    indexMdPath: typeof item.index_md_path === "string" ? item.index_md_path : null,
    isActive: item.is_active !== false,
    updatedAt: typeof item.updated_at === "string" ? item.updated_at : new Date().toISOString(),
  };
}

function normalizeDirectory(raw: unknown): DirectoryItem | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const item = raw as {
    path?: unknown;
    display_name?: unknown;
  };

  if (
    typeof item.path !== "string" ||
    typeof item.display_name !== "string"
  ) {
    return null;
  }

  return {
    path: item.path,
    displayName: item.display_name,
  };
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function buildParentPath(currentPath: string): string {
  const normalized = currentPath.trim();
  if (!normalized || normalized === "/") {
    return "/";
  }

  const trimmed = normalized.replace(/\/+$/, "");
  const separatorIndex = trimmed.lastIndexOf("/");
  if (separatorIndex <= 0) {
    return "/";
  }

  return trimmed.slice(0, separatorIndex);
}

function inferProjectNameFromPath(absolutePath: string): string {
  const trimmed = absolutePath.trim().replace(/\/+$/, "");
  if (!trimmed) {
    return "";
  }
  const parts = trimmed.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

function rootPathInput({
  value,
  onChange,
  onBrowse,
  disabled,
}: {
  value: string;
  onChange: (nextValue: string) => void;
  onBrowse: () => void;
  disabled: boolean;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <label className="text-sm">
        <span className="mb-1.5 block font-medium text-foreground">Root path</span>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="/root/codexchat"
          className="w-full rounded-xl border border-border bg-background px-3 py-2 font-mono text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
        />
      </label>
      <button
        type="button"
        className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 text-sm font-medium transition hover:bg-muted"
        onClick={onBrowse}
        disabled={disabled}
      >
        <FolderSearch className="h-4 w-4" />
        Browse
      </button>
    </div>
  );
}

export default function ProjectsPlaceholderPageClient() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [isSubmitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<ProjectFormState>(EMPTY_FORM);
  const [editingByProjectId, setEditingByProjectId] = useState<Record<string, ProjectFormState>>({});
  const [directoryTarget, setDirectoryTarget] = useState<DirectoryPickerTarget>(null);
  const [directoryPath, setDirectoryPath] = useState("");
  const [directoryAbsolutePath, setDirectoryAbsolutePath] = useState("");
  const [directoryItems, setDirectoryItems] = useState<DirectoryItem[]>([]);
  const [directorySearchQuery, setDirectorySearchQuery] = useState("");
  const [directorySearchResults, setDirectorySearchResults] = useState<DirectoryItem[]>([]);
  const [isDirectoryLoading, setDirectoryLoading] = useState(false);
  const [isDirectorySearching, setDirectorySearching] = useState(false);
  const [directoryErrorMessage, setDirectoryErrorMessage] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch("/api/projects?include_inactive=true", {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      });
      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }
      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`);
      }
      const payload = (await response.json()) as { projects?: unknown[] };
      const normalized = Array.isArray(payload.projects)
        ? payload.projects.map((item) => normalizeProject(item)).filter((item): item is ProjectItem => Boolean(item))
        : [];
      setProjects(normalized);
    } catch {
      setErrorMessage("Unable to load projects right now.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  const loadDirectoryBrowser = useCallback(
    async (nextPath: string) => {
      setDirectoryLoading(true);
      setDirectoryErrorMessage(null);
      try {
        const query = nextPath ? `?path=${encodeURIComponent(nextPath)}` : "";
        const response = await fetch(`/api/projects/host/directories/browse${query}`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });
        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }
        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
          throw new Error(payload?.error?.message ?? "Directory browser is unavailable.");
        }
        const payload = (await response.json()) as {
          path?: unknown;
          absolute_path?: unknown;
          items?: unknown[];
        };
        setDirectoryPath(typeof payload.path === "string" ? payload.path : "");
        setDirectoryAbsolutePath(typeof payload.absolute_path === "string" ? payload.absolute_path : "");
        setDirectoryItems(
          Array.isArray(payload.items)
            ? payload.items.map((item) => normalizeDirectory(item)).filter((item): item is DirectoryItem => Boolean(item))
            : [],
        );
      } catch (error) {
        setDirectoryErrorMessage(error instanceof Error ? error.message : "Directory browser is unavailable.");
      } finally {
        setDirectoryLoading(false);
      }
    },
    [router],
  );

  const searchDirectories = useCallback(
    async (query: string, nextPath: string) => {
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        setDirectorySearchResults([]);
        return;
      }

      setDirectorySearching(true);
      setDirectoryErrorMessage(null);
      try {
        const searchParams = new URLSearchParams({ q: trimmedQuery });
        if (nextPath) {
          searchParams.set("path", nextPath);
        }
        const response = await fetch(`/api/projects/host/directories/search?${searchParams.toString()}`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });
        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }
        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
          throw new Error(payload?.error?.message ?? "Directory search is unavailable.");
        }
        const payload = (await response.json()) as { items?: unknown[] };
        setDirectorySearchResults(
          Array.isArray(payload.items)
            ? payload.items.map((item) => normalizeDirectory(item)).filter((item): item is DirectoryItem => Boolean(item))
            : [],
        );
      } catch (error) {
        setDirectoryErrorMessage(error instanceof Error ? error.message : "Directory search is unavailable.");
      } finally {
        setDirectorySearching(false);
      }
    },
    [router],
  );

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const openDirectoryPicker = (target: DirectoryPickerTarget) => {
    setDirectoryTarget(target);
    setDirectorySearchQuery("");
    setDirectorySearchResults([]);
    setDirectoryErrorMessage(null);
    void loadDirectoryBrowser("/");
  };

  const applyDirectorySelection = (absolutePath: string) => {
    if (!directoryTarget) {
      return;
    }

    if (directoryTarget.kind === "create") {
      setCreateForm((previous) => ({
        ...previous,
        rootPath: absolutePath,
        name: previous.name.trim() ? previous.name : inferProjectNameFromPath(absolutePath),
      }));
    } else {
      setEditingByProjectId((previous) => {
        const existing = previous[directoryTarget.projectId];
        const currentProject = projects.find((item) => item.id === directoryTarget.projectId);
        const nextDraft: ProjectFormState = existing ?? {
          name: currentProject?.name ?? "",
          rootPath: currentProject?.rootPath ?? "",
          indexMdPath: currentProject?.indexMdPath ?? "",
        };

        return {
          ...previous,
          [directoryTarget.projectId]: {
            ...nextDraft,
            rootPath: absolutePath,
          },
        };
      });
    }

    setDirectoryTarget(null);
  };

  const submitCreate = async () => {
    setSubmitting(true);
    setSubmitMessage(null);
    setErrorMessage(null);
    try {
      const response = await fetch("/api/projects", {
        method: "POST",
        credentials: "include",
        headers: withCsrfHeader({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          name: createForm.name,
          root_path: createForm.rootPath,
          index_md_path: createForm.indexMdPath.trim() || null,
        }),
      });
      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
        throw new Error(payload?.error?.message ?? "Project creation failed.");
      }
      const payload = (await response.json()) as { project?: unknown };
      const project = normalizeProject(payload.project);
      if (!project) {
        throw new Error("Project creation returned an invalid payload.");
      }
      setProjects((previous) => [project, ...previous.filter((item) => item.id !== project.id)]);
      setCreateForm(EMPTY_FORM);
      setSubmitMessage("Project created.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Project creation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitPatch = async (projectId: string) => {
    const draft = editingByProjectId[projectId];
    if (!draft) {
      return;
    }

    setSubmitting(true);
    setSubmitMessage(null);
    setErrorMessage(null);
    try {
      const existing = projects.find((item) => item.id === projectId);
      const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "PATCH",
        credentials: "include",
        headers: withCsrfHeader({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          name: draft.name,
          root_path: draft.rootPath,
          index_md_path: draft.indexMdPath.trim() || null,
          is_active: existing?.isActive ?? true,
        }),
      });
      if (response.status === 401 || response.status === 403) {
        router.replace("/login");
        return;
      }
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
        throw new Error(payload?.error?.message ?? "Project update failed.");
      }
      const payload = (await response.json()) as { project?: unknown };
      const project = normalizeProject(payload.project);
      if (!project) {
        throw new Error("Project update returned an invalid payload.");
      }
      setProjects((previous) => previous.map((item) => (item.id === project.id ? project : item)));
      setEditingByProjectId((previous) => {
        const next = { ...previous };
        delete next[projectId];
        return next;
      });
      setSubmitMessage("Project updated.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Project update failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (project: ProjectItem) => {
    setSubmitting(true);
    setSubmitMessage(null);
    setErrorMessage(null);
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, {
        method: "PATCH",
        credentials: "include",
        headers: withCsrfHeader({ "Content-Type": "application/json" }),
        body: JSON.stringify({ is_active: !project.isActive }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
        throw new Error(payload?.error?.message ?? "Project update failed.");
      }
      const payload = (await response.json()) as { project?: unknown };
      const normalized = normalizeProject(payload.project);
      if (!normalized) {
        throw new Error("Project update returned an invalid payload.");
      }
      setProjects((previous) => previous.map((item) => (item.id === normalized.id ? normalized : item)));
      setSubmitMessage(normalized.isActive ? "Project activated." : "Project archived from active selection.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Project update failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const visibleDirectoryResults = directorySearchQuery.trim() ? directorySearchResults : directoryItems;

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="rounded-[28px] border border-border/80 bg-background/92 p-6 shadow-[0_12px_40px_rgba(0,0,0,0.05)] backdrop-blur sm:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
              Projects
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Project selection now drives chat context.
            </h1>
            <p className="mt-3 max-w-3xl text-sm text-muted-foreground sm:text-base">
              Add the VPS directories the assistant should recognize. When a shared conversation becomes project-specific, chat can bind to one of these projects and inject the matching root path into the turn context.
            </p>
          </div>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-sm font-medium transition hover:bg-muted"
            onClick={() => void loadProjects()}
            disabled={isLoading || isSubmitting}
          >
            <RefreshCcw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="rounded-[24px] border border-border bg-background/90 p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <FolderKanban className="h-6 w-6 text-foreground" />
            <div>
              <h2 className="text-xl font-semibold tracking-tight">Known projects</h2>
              <p className="text-sm text-muted-foreground">
                Active projects appear in clarification prompts. Inactive ones remain stored but stop appearing as options.
              </p>
            </div>
          </div>

          {errorMessage ? (
            <div className="mt-4 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {errorMessage}
            </div>
          ) : null}

          {submitMessage ? (
            <div className="mt-4 rounded-2xl border border-border bg-muted/40 px-4 py-3 text-sm text-foreground">
              {submitMessage}
            </div>
          ) : null}

          {isLoading ? (
            <div className="mt-5 space-y-3">
              <div className="h-24 animate-pulse rounded-2xl border border-border bg-muted/40" />
              <div className="h-24 animate-pulse rounded-2xl border border-border bg-muted/40" />
            </div>
          ) : projects.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-6 text-sm text-muted-foreground">
              No projects yet. Add at least one project root so chat can clarify ambiguous project-specific turns.
            </div>
          ) : (
            <div className="mt-5 grid gap-4">
              {projects.map((project) => {
                const draft = editingByProjectId[project.id] ?? {
                  name: project.name,
                  rootPath: project.rootPath,
                  indexMdPath: project.indexMdPath ?? "",
                };

                return (
                  <article
                    key={project.id}
                    className="rounded-[22px] border border-border bg-background p-4 shadow-[0_10px_24px_rgba(0,0,0,0.03)]"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold tracking-tight">{project.name}</h3>
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] ${project.isActive ? "border border-border bg-muted/50 text-foreground" : "border border-border/70 bg-background text-muted-foreground"}`}>
                            {project.isActive ? "Active" : "Inactive"}
                          </span>
                        </div>
                        <p className="mt-1 break-all text-sm text-muted-foreground">{project.rootPath}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                          Updated {formatUpdatedAt(project.updatedAt)}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="rounded-xl border border-border px-3 py-2 text-sm font-medium transition hover:bg-muted"
                        onClick={() => void toggleActive(project)}
                        disabled={isSubmitting}
                      >
                        {project.isActive ? "Deactivate" : "Activate"}
                      </button>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <label className="text-sm">
                        <span className="mb-1.5 block font-medium text-foreground">Name</span>
                        <input
                          value={draft.name}
                          onChange={(event) =>
                            setEditingByProjectId((previous) => ({
                              ...previous,
                              [project.id]: { ...draft, name: event.target.value },
                            }))
                          }
                          className="w-full rounded-xl border border-border bg-background px-3 py-2 outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
                        />
                      </label>
                      <div className="sm:col-span-2">
                        {rootPathInput({
                          value: draft.rootPath,
                          onChange: (nextValue) =>
                            setEditingByProjectId((previous) => ({
                              ...previous,
                              [project.id]: { ...draft, rootPath: nextValue },
                            })),
                          onBrowse: () => openDirectoryPicker({ kind: "edit", projectId: project.id }),
                          disabled: isSubmitting,
                        })}
                      </div>
                      <label className="text-sm sm:col-span-2">
                        <span className="mb-1.5 block font-medium text-foreground">Index markdown path</span>
                        <input
                          value={draft.indexMdPath}
                          onChange={(event) =>
                            setEditingByProjectId((previous) => ({
                              ...previous,
                              [project.id]: { ...draft, indexMdPath: event.target.value },
                            }))
                          }
                          placeholder="Optional absolute path to INDEX.md"
                          className="w-full rounded-xl border border-border bg-background px-3 py-2 font-mono text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
                        />
                      </label>
                    </div>

                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-medium transition hover:bg-muted"
                        onClick={() => void submitPatch(project.id)}
                        disabled={isSubmitting}
                      >
                        <Save className="h-4 w-4" />
                        Save changes
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-6">
          <section className="rounded-[24px] border border-border bg-background/90 p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <Plus className="h-5 w-5 text-foreground" />
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Add project</h2>
                <p className="text-sm text-muted-foreground">
                  Pick any reachable VPS directory from the browser or paste an absolute path manually.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="text-sm">
                <span className="mb-1.5 block font-medium text-foreground">Project name</span>
                <input
                  value={createForm.name}
                  onChange={(event) => setCreateForm((previous) => ({ ...previous, name: event.target.value }))}
                  placeholder="agentmobile"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
                />
              </label>
              {rootPathInput({
                value: createForm.rootPath,
                onChange: (nextValue) => setCreateForm((previous) => ({ ...previous, rootPath: nextValue })),
                onBrowse: () => openDirectoryPicker({ kind: "create" }),
                disabled: isSubmitting,
              })}
              <label className="text-sm">
                <span className="mb-1.5 block font-medium text-foreground">Index markdown path</span>
                <input
                  value={createForm.indexMdPath}
                  onChange={(event) => setCreateForm((previous) => ({ ...previous, indexMdPath: event.target.value }))}
                  placeholder="/root/codexchat/INDEX.md"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 font-mono text-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
                />
              </label>
            </div>

            <button
              type="button"
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-foreground px-4 py-2.5 text-sm font-semibold text-background transition hover:opacity-90"
              onClick={() => void submitCreate()}
              disabled={isSubmitting}
            >
              <Plus className="h-4 w-4" />
              Create project
            </button>
          </section>

          <section className="rounded-[24px] border border-border bg-background/90 p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <FolderSearch className="h-5 w-5 text-foreground" />
              <div>
                <h2 className="text-xl font-semibold tracking-tight">Directory finder</h2>
                <p className="text-sm text-muted-foreground">
                  Search or browse directories across the VPS filesystem and apply one to a project root path.
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Target
              </p>
              <p className="mt-1 text-sm text-foreground">
                {directoryTarget?.kind === "create"
                  ? "New project form"
                  : directoryTarget?.kind === "edit"
                    ? `Editing ${projects.find((item) => item.id === directoryTarget.projectId)?.name ?? "project"}`
                    : "Choose Browse beside any root path field to start selecting a directory."}
              </p>
            </div>

            <div className="mt-4 grid gap-3">
              <label className="text-sm">
                <span className="mb-1.5 block font-medium text-foreground">Search directories</span>
                <div className="flex gap-2">
                  <input
                    value={directorySearchQuery}
                    onChange={(event) => setDirectorySearchQuery(event.target.value)}
                    placeholder="Search current directory tree"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/10"
                  />
                  <button
                    type="button"
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 text-sm font-medium transition hover:bg-muted"
                    onClick={() => void searchDirectories(directorySearchQuery, directoryPath)}
                    disabled={isDirectorySearching}
                  >
                    <Search className="h-4 w-4" />
                    Search
                  </button>
                </div>
              </label>

              <div className="flex flex-wrap items-center gap-2 text-sm">
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => void loadDirectoryBrowser(buildParentPath(directoryPath))}
                  disabled={isDirectoryLoading || !directoryPath}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Up
                </button>
                <button
                  type="button"
                  className="rounded-xl border border-border bg-background px-3 py-2 font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => void loadDirectoryBrowser(directoryPath)}
                  disabled={isDirectoryLoading}
                >
                  Refresh folders
                </button>
                <button
                  type="button"
                  className="rounded-xl border border-border bg-background px-3 py-2 font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => applyDirectorySelection(directoryAbsolutePath)}
                  disabled={!directoryTarget || !directoryAbsolutePath}
                >
                  Use current folder
                </button>
                {directoryTarget ? (
                  <button
                    type="button"
                    className="rounded-xl border border-border bg-background px-3 py-2 font-medium transition hover:bg-muted"
                    onClick={() => setDirectoryTarget(null)}
                  >
                    Cancel
                  </button>
                ) : null}
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-border bg-muted/30 px-4 py-3 text-sm">
              <p className="font-medium text-foreground">Current folder</p>
              <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                {directoryAbsolutePath || "Open the browser to load the VPS root directory."}
              </p>
            </div>

            {directoryErrorMessage ? (
              <div className="mt-4 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {directoryErrorMessage}
              </div>
            ) : null}

            <div className="mt-4 rounded-[22px] border border-border bg-background p-3">
              {isDirectoryLoading || isDirectorySearching ? (
                <div className="space-y-2">
                  <div className="h-12 animate-pulse rounded-2xl border border-border bg-muted/40" />
                  <div className="h-12 animate-pulse rounded-2xl border border-border bg-muted/40" />
                </div>
              ) : visibleDirectoryResults.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border bg-muted/20 px-4 py-6 text-sm text-muted-foreground">
                  {directorySearchQuery.trim()
                    ? "No matching directories in the current area."
                    : "No subdirectories found here yet. You can still use the current folder."}
                </div>
              ) : (
                <div className="grid gap-2">
                  {visibleDirectoryResults.map((item) => (
                    <button
                      key={item.path}
                      type="button"
                      className="rounded-2xl border border-border bg-background px-4 py-3 text-left transition hover:bg-muted"
                      onClick={() =>
                        directorySearchQuery.trim()
                          ? applyDirectorySelection(item.path)
                          : void loadDirectoryBrowser(item.path)
                      }
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-foreground">{item.displayName}</span>
                        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                          {directorySearchQuery.trim() ? "Use" : "Open"}
                        </span>
                      </div>
                      <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                        {item.path}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}
