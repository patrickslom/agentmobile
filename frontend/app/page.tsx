import { Coffee } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import WinkingLogo from "./components/winking-logo";
import HomeLogoutToast from "./components/home-logout-toast";
import { getAuthenticatedUser } from "@/lib/auth-session";

type HomePageProps = {
  searchParams: Promise<{ logged_out?: string }>;
};

export default async function Home({ searchParams }: HomePageProps) {
  if (await getAuthenticatedUser()) {
    redirect("/chat");
  }

  const params = await searchParams;
  const wasLoggedOut = params.logged_out === "1";

  return (
    <main className="min-h-screen bg-background px-6 py-20 text-foreground">
      <HomeLogoutToast show={wasLoggedOut} />
      <section className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        <div className="flex items-center gap-3">
          <WinkingLogo />
          <p className="text-xs font-semibold tracking-[0.2em] uppercase">
            AGENTMOBILE
          </p>
        </div>

        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
          From fresh VPS to live Mobile chat in minutes.
        </h1>

        <p className="max-w-3xl text-base text-zinc-700 sm:text-lg dark:text-zinc-300">
          Run the installer, open your domain, log in, and start streaming
          Agent responses from desktop or phone.
        </p>

        <p className="max-w-3xl text-base text-zinc-700 sm:text-lg dark:text-zinc-300">
          No Telegram flow. Just a clean web app for real chat workflows and
          file-based collaboration.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/login"
            className="inline-flex rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background transition hover:opacity-90"
          >
            Go to login
          </Link>
          <a
            href="https://www.buymeacoffee.com/patrickslom"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-black bg-[#FFDD00] px-5 py-2.5 text-sm font-medium text-black transition hover:brightness-95"
          >
            <Coffee className="h-4 w-4" aria-hidden="true" />
            Buy me a coffee
          </a>
        </div>
      </section>
    </main>
  );
}
