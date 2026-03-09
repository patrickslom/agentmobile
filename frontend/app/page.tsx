import Link from "next/link";
import Script from "next/script";
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
      <section className="mx-auto grid w-full max-w-6xl gap-12 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="flex flex-col gap-8">
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

          <div>
            <Link
              href="/login"
              className="inline-flex rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background transition hover:opacity-90"
            >
              Go to login
            </Link>
          </div>
        </div>

        <aside className="order-last rounded-2xl border border-border bg-muted p-6 shadow-sm lg:order-none lg:sticky lg:top-8">
          <p className="text-xs font-semibold tracking-[0.2em] text-foreground uppercase">
            Support AgentMobile
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-foreground">
            Buy me a coffee
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
            Like the project? If AgentMobile helps you out, buying a coffee is
            a simple way to support continued development.
          </p>
          <div className="mt-6">
            <a
              href="https://www.buymeacoffee.com/patrickslom"
              target="_blank"
              rel="noreferrer"
              className="inline-flex rounded-lg bg-[#5F7FFF] px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Support on Buy Me a Coffee
            </a>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            The floating coffee widget is also available on this page.
          </p>
        </aside>
      </section>
      <Script
        id="buy-me-a-coffee-widget"
        src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js"
        strategy="afterInteractive"
        data-name="BMC-Widget"
        data-cfasync="false"
        data-id="patrickslom"
        data-description="Support me on Buy me a coffee!"
        data-message="Like the project? If AgentMobile helps you out, buying a coffee is a great way to support continued development."
        data-color="#5F7FFF"
        data-position="Right"
        data-x_margin="18"
        data-y_margin="18"
      />
    </main>
  );
}
