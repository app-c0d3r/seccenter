/**
 * SSE stream client for AI agent communication
 * Uses native fetch + getReader() because Layer 2 requires POST with JSON body
 */

import type { ReportDraft } from "@/types/agent";

const BASE_URL = "/api";

/** Callback interface for SSE event handling */
export interface SSECallbacks {
  onToken: (content: string) => void;
  onReportDraft: (draft: ReportDraft) => void;
  onReportSection: (section: Record<string, unknown>) => void;
  onToolCall: (tool: string) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

/**
 * Consume an SSE response stream, buffering until complete events arrive.
 * Dispatches parsed events to the provided callbacks.
 */
async function consumeStream(
  response: Response,
  callbacks: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        reader.cancel();
        break;
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (delimited by double newline)
      while (buffer.includes("\n\n")) {
        const idx = buffer.indexOf("\n\n");
        const eventStr = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);

        if (!eventStr) continue;

        // Parse SSE event fields
        let eventType = "";
        let dataStr = "";
        for (const line of eventStr.split("\n")) {
          if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataStr = line.slice(5).trim();
          }
        }

        if (!eventType || !dataStr) continue;

        // Parse JSON data and dispatch to callbacks
        try {
          const data = JSON.parse(dataStr) as Record<string, unknown>;

          switch (eventType) {
            case "token":
              callbacks.onToken((data.content as string) ?? "");
              break;
            case "report_draft":
              callbacks.onReportDraft(data as unknown as ReportDraft);
              break;
            case "report_section":
              callbacks.onReportSection(data);
              break;
            case "tool_call":
              callbacks.onToolCall((data.tool as string) ?? "");
              break;
            case "error":
              callbacks.onError((data.message as string) ?? "Unknown error");
              break;
            case "done":
              callbacks.onDone();
              break;
          }
        } catch {
          callbacks.onError(`Failed to parse SSE data: ${dataStr}`);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Layer 1: Stream automated analysis for a session (GET request)
 */
export async function streamAnalysis(
  sessionId: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/sessions/${sessionId}/agent/stream`,
    { signal, headers: { Accept: "text/event-stream" } },
  );

  if (!response.ok) {
    callbacks.onError(`Analysis request failed: ${response.status}`);
    return;
  }

  await consumeStream(response, callbacks, signal);
}

/**
 * Layer 2: Stream chat response for a session (POST request)
 */
export async function streamChat(
  sessionId: string,
  message: string,
  reportDraft: ReportDraft,
  callbacks: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/sessions/${sessionId}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, report_draft: reportDraft }),
    signal,
  });

  if (!response.ok) {
    callbacks.onError(`Chat request failed: ${response.status}`);
    return;
  }

  await consumeStream(response, callbacks, signal);
}
