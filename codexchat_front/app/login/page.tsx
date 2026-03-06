import Link from "next/link";
import { redirect } from "next/navigation";
import WinkingLogo from "../components/winking-logo";
import { hasSessionCookie } from "@/lib/auth-session";
import LoginForm from "./login-form";

type LoginPageProps = {
  searchParams: Promise<{ logged_out?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  if (await hasSessionCookie()) {
    redirect("/chat");
  }

  const params = await searchParams;
  const wasLoggedOut = params.logged_out === "1";

  return (
    <section className="mx-auto flex min-h-screen min-h-dvh w-full max-w-md items-center px-6 py-12">
      <div className="w-full rounded-2xl border border-border bg-background p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <WinkingLogo size={56} />
          <p className="text-xs font-semibold tracking-[0.18em] uppercase text-zinc-500 dark:text-zinc-400">
            CodexChat
          </p>
        </div>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
          Continue to a new chat and resume previous conversations from your
          sidebar history.
        </p>

        {wasLoggedOut ? (
          <p className="mt-4 rounded-lg border border-border bg-muted px-3 py-2 text-sm text-zinc-700 dark:text-zinc-200">
            You have been logged out.
          </p>
        ) : null}

        <LoginForm />

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
