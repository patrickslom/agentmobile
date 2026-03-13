import { redirect } from "next/navigation";
import ProtectedShell from "@/components/app/protected-shell";
import { getAuthenticatedUser, hasSessionCookie } from "@/lib/auth-session";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authenticated = await hasSessionCookie();

  if (!authenticated) {
    redirect("/login");
  }

  const user = await getAuthenticatedUser();

  return <ProtectedShell isAdmin={user?.role === "admin"}>{children}</ProtectedShell>;
}
