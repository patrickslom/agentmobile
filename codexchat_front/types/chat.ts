export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  pending?: boolean;
  deliveryStatus?: "sending" | "failed";
};

export type AssistantDeltaEvent = {
  type: "assistant_delta";
  conversationId?: string;
  conversation_id?: string;
  delta?: string;
  content?: string;
};

export type AssistantDoneEvent = {
  type: "assistant_done";
  conversationId?: string;
  conversation_id?: string;
  content?: string;
  message?: string;
  text?: string;
};

export type ChatErrorEvent = {
  type: "error";
  conversationId?: string;
  conversation_id?: string;
  code?: string;
  message?: string;
  details?: {
    conversationId?: string;
    conversation_id?: string;
    busy?: boolean;
  };
};

export type ConversationBusyEvent = {
  type: "conversation_busy" | "thread_busy";
  conversationId?: string;
  conversation_id?: string;
  busy?: boolean;
};

export type ConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";
