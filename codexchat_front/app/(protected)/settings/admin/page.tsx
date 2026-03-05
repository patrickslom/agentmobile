import Link from "next/link";
import { redirect } from "next/navigation";
import { isAuthenticatedAdmin } from "@/lib/auth-session";

export default async function AdminSettingsPage() {
  const isAdmin = await isAuthenticatedAdmin();
  if (!isAdmin) {
    redirect("/settings");
  }

  return (
    <section className="rounded-xl border border-border bg-muted p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Admin Settings</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Admin-only settings route is ready at <code>/settings/admin</code>.
      </p>
      <Link
        href="/settings"
        className="mt-4 inline-flex text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        Back to settings
      </Link>
    </section>
  );
}
