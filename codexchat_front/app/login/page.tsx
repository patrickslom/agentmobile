import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import WinkingLogo from "../components/winking-logo";

const SESSION_COOKIE_KEYS = [
  "codexchat_session",
  "session",
  "session_id",
  "auth_session",
] as const;

export default async function LoginPage() {
  const cookieStore = await cookies();
  const hasSession = SESSION_COOKIE_KEYS.some((cookieKey) =>
    Boolean(cookieStore.get(cookieKey)?.value),
  );

  if (hasSession) {
    redirect("/chat");
  }

  return (
    <section className="mx-auto flex min-h-screen min-h-dvh w-full max-w-md items-center px-6 py-12">
      <div className="w-full rounded-2xl border border-zinc-300 bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-black">
        <div className="flex items-center gap-3">
          <WinkingLogo size={56} />
          <p className="text-xs font-semibold tracking-[0.18em] uppercase text-zinc-500 dark:text-zinc-400">
            CodexChat
          </p>
        </div>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-black dark:text-zinc-100">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
          Continue to a new chat and resume previous conversations from your
          sidebar history.
        </p>

        <form className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium text-zinc-800 dark:text-zinc-200">
              Email
            </span>
            <input
              type="email"
              name="email"
              autoComplete="email"
              required
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-black dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-zinc-300"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium text-zinc-800 dark:text-zinc-200">
              Password
            </span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-black dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-zinc-300"
            />
          </label>

          <button
            type="submit"
            className="mt-2 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-300"
          >
            Sign in
          </button>
        </form>

        <Link
          href="/"
          className="mt-4 inline-flex text-sm text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-300"
        >
          Back to home
        </Link>
      </div>
    </section>
  );
}
