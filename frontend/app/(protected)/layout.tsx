import { redirect } from "next/navigation";
import { hasSessionCookie } from "@/lib/auth-session";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authenticated = await hasSessionCookie();

  if (!authenticated) {
    redirect("/login");
  }

  return children;
}
