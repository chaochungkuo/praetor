import type { AgentMessage, ApiEnvelope, ConversationResult, OfficeSnapshot, Session, TimelineEvent } from "./types";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error?.message ?? `Request failed: ${response.status}`);
  }
  return payload.data;
}

export async function getSession(): Promise<Session> {
  return api<Session>("/auth/session");
}

export async function getOfficeSnapshot(): Promise<OfficeSnapshot> {
  return api<OfficeSnapshot>("/api/office/snapshot");
}

export async function sendCeoMessage(body: string, csrfToken: string): Promise<ConversationResult> {
  return api<ConversationResult>("/api/office/conversation", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: JSON.stringify({ body })
  });
}

export async function getMissionTimeline(missionId: string): Promise<TimelineEvent[]> {
  const data = await api<{ events: TimelineEvent[] }>(`/api/missions/${missionId}/timeline`);
  return data.events;
}

export async function getMissionAgentMessages(missionId: string): Promise<AgentMessage[]> {
  const data = await api<{ messages: AgentMessage[] }>(`/api/missions/${missionId}/agent-messages`);
  return data.messages;
}
