import { NextResponse } from "next/server";
import { SESSION_COOKIE_KEYS, resolveServerApiBaseUrl } from "@/lib/auth-session";

export async function POST(request: Request) {
  const apiBaseUrl = await resolveServerApiBaseUrl();

  if (apiBaseUrl) {
    try {
      await fetch(`${apiBaseUrl}/auth/logout`, {
        method: "POST",
        headers: request.headers.get("cookie")
          ? { cookie: request.headers.get("cookie") as string }
          : undefined,
        cache: "no-store",
      });
    } catch {
      // Local cookie expiration below still logs out frontend state.
    }
  }

  const response = new NextResponse(null, {
    status: 303,
    headers: {
      location: "/?logged_out=1",
    },
  });

  for (const cookieName of SESSION_COOKIE_KEYS) {
    response.cookies.set(cookieName, "", {
      expires: new Date(0),
      path: "/",
    });
  }

  return response;
}
