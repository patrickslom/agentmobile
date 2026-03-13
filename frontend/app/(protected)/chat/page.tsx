"use client";

import ChatHomePageClient from "@/components/chat/chat-home-page-client";
import ChatWorkspace from "@/components/chat/chat-workspace";
import { useSearchParams } from "next/navigation";

function ChatPageClient() {
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("conversationId");

  if (conversationId) {
    return <ChatWorkspace />;
  }

  return <ChatHomePageClient />;
}

export default function ChatPage() {
  return <ChatPageClient />;
}
