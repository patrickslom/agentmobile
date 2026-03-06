import { redirect } from "next/navigation";
import AdminSettingsPageClient from "@/components/settings/admin-settings-page-client";
import { isAuthenticatedAdmin } from "@/lib/auth-session";

export default async function AdminSettingsPage() {
  const isAdmin = await isAuthenticatedAdmin();
  if (!isAdmin) {
    redirect("/settings");
  }

  return <AdminSettingsPageClient />;
}
