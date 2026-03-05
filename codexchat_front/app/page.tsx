import Link from "next/link";
import WinkingLogo from "./components/winking-logo";

export default function Home() {
  return (
    <main className="min-h-screen bg-background px-6 py-20 text-foreground">
      <section className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        <div className="flex items-center gap-3">
          <WinkingLogo />
          <p className="text-xs font-semibold tracking-[0.2em] uppercase">
            CodexChat
          </p>
        </div>

        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
          From fresh VPS to live Codex chat in minutes.
        </h1>

        <p className="max-w-3xl text-base text-zinc-700 sm:text-lg dark:text-zinc-300">
          Run the installer, open your domain, log in, and start streaming
          Codex responses from desktop or phone.
        </p>

        <p className="max-w-3xl text-base text-zinc-700 sm:text-lg dark:text-zinc-300">
          No Telegram flow. Just a clean web app for real chat workflows and
          file-based collaboration.
        </p>

        <div>
          <Link
            href="/login"
            className="inline-flex rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background transition hover:opacity-90"
          >
            Go to login
          </Link>
        </div>
      </section>
    </main>
  );
}
