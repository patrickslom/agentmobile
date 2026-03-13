import { redirect } from "next/navigation";
import AdminSettingsPageClient from "@/components/settings/admin-settings-page-client";
import { getAuthenticatedUser } from "@/lib/auth-session";

export default async function AdminPage() {
  const user = await getAuthenticatedUser();

  if (user?.role !== "admin") {
    redirect("/settings");
  }

  return <AdminSettingsPageClient />;
}
