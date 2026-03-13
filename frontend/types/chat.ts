export type ChatRole = "user" | "assistant" | "system";

export type ChatMessageFile = {
  id: string;
  originalName: string;
  storagePath: string;
  downloadPath: string;
  mimeType?: string;
  sizeBytes?: number;
};

export type WorkspaceFileRef = {
  kind: "workspace";
  relativePath: string;
  displayName: string;
};

export type ProjectSummary = {
  id: string;
  name: string;
  rootPath: string;
  indexMdPath?: string | null;
  isActive: boolean;
};

export type PendingProjectClarification = {
  state: "awaiting_selection" | "awaiting_create";
  question: string;
  options?: Array<{
    number: number;
    id: string;
    label: string;
    name?: string;
    rootPath?: string;
  }>;
  allowCreate?: boolean;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  isBookmarked?: boolean;
  isBookmarkedByCurrentUser?: boolean;
  authorUserId?: string;
  authorDisplayName?: string;
  authorProfilePictureUrl?: string;
  isCurrentUserAuthor?: boolean;
  createdAt: string;
  clientMessageId?: string;
  files?: ChatMessageFile[];
  workspaceRefs?: WorkspaceFileRef[];
  pending?: boolean;
  partial?: boolean;
  turnStatus?: "completed" | "failed" | "timed_out" | "stopped";
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
  message_id?: string;
  content?: string;
  message?: string;
  text?: string;
  status?: "completed" | "failed" | "timed_out" | "stopped";
  partial?: boolean;
};

export type AssistantWaitingEvent = {
  type: "assistant_waiting";
  conversationId?: string;
  conversation_id?: string;
};

export type AssistantClarifyEvent = {
  type: "assistant_clarify";
  conversationId?: string;
  conversation_id?: string;
  question?: string;
  expected_reply?: "number";
  allow_create?: boolean;
  options?: Array<{
    number?: number;
    id?: string;
    label?: string;
    name?: string;
    root_path?: string;
  }>;
};

export type AssistantProjectCreateEvent = {
  type: "assistant_project_create";
  conversationId?: string;
  conversation_id?: string;
  question?: string;
};

export type MessageCreatedEvent = {
  type: "message_created";
  conversationId?: string;
  conversation_id?: string;
  message?: {
    id?: string;
    role?: string;
    content?: string;
    author_user_id?: string | null;
    author_display_name?: string | null;
    author_profile_picture_url?: string | null;
    is_current_user_author?: boolean | null;
    created_at?: string;
    client_message_id?: string | null;
    files?: unknown;
    metadata_json?: {
      workspace_refs?: unknown;
      partial?: unknown;
      turn_status?: unknown;
    };
  };
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
  type: "conversation_busy" | "thread_busy" | "thread_busy_state";
  conversationId?: string;
  conversation_id?: string;
  busy?: boolean;
  is_busy?: boolean;
};

export type ConversationProjectStateEvent = {
  type: "conversation_project_state";
  conversationId?: string;
  conversation_id?: string;
  project_mode?: "unknown" | "general" | "project_bound";
  project?: {
    id?: string;
    name?: string;
    root_path?: string;
    index_md_path?: string | null;
    is_active?: boolean;
  } | null;
  pending_project_clarification?: {
    state?: "awaiting_selection" | "awaiting_create";
    question?: string;
    options?: Array<{
      number?: number;
      id?: string;
      label?: string;
      name?: string;
      root_path?: string;
    }>;
    allow_create?: boolean;
  } | null;
};

export type ConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";
