import SettingsPageClient from "@/components/settings/settings-page-client";
import { getAuthenticatedUser } from "@/lib/auth-session";

export default async function SettingsPage() {
  const user = await getAuthenticatedUser();
  const isAdmin = user?.role === "admin";

  return <SettingsPageClient isAdmin={isAdmin} />;
}
