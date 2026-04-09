/**
 * Button that triggers Layer 1 automated analysis.
 * Streams AI response into chat and populates report canvas.
 */
import { useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { streamAnalysis } from "@/api/sseClient";
import { useSessionStore } from "@/store/sessionStore";

export function AnalyzeButton() {
  const abortRef = useRef<AbortController | null>(null);

  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const agentStreaming = useSessionStore((s) => s.agentStreaming);
  const addChatMessage = useSessionStore((s) => s.addChatMessage);
  const appendToLastAssistantMessage = useSessionStore(
    (s) => s.appendToLastAssistantMessage,
  );
  const setReportDraft = useSessionStore((s) => s.setReportDraft);
  const patchReportSection = useSessionStore((s) => s.patchReportSection);
  const setAgentStreaming = useSessionStore((s) => s.setAgentStreaming);

  const handleAnalyze = useCallback(async () => {
    if (!activeSessionId || agentStreaming) return;

    // Add a system-initiated assistant message for streaming
    addChatMessage(activeSessionId, {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    });

    setAgentStreaming(true);
    abortRef.current = new AbortController();

    try {
      await streamAnalysis(
        activeSessionId,
        {
          onToken: (content) =>
            appendToLastAssistantMessage(activeSessionId, content),
          onReportDraft: (draft) => setReportDraft(activeSessionId, draft),
          onReportSection: (section) => {
            const key = Object.keys(section)[0];
            if (key) {
              patchReportSection(
                activeSessionId,
                key,
                section[key] as Record<string, unknown>,
              );
            }
          },
          onToolCall: () => {},
          onError: (msg) =>
            appendToLastAssistantMessage(
              activeSessionId,
              `\n\n**Error:** ${msg}`,
            ),
          onDone: () => {},
        },
        abortRef.current.signal,
      );
    } finally {
      setAgentStreaming(false);
      abortRef.current = null;
    }
  }, [
    activeSessionId,
    agentStreaming,
    addChatMessage,
    appendToLastAssistantMessage,
    setReportDraft,
    patchReportSection,
    setAgentStreaming,
  ]);

  return (
    <Button
      onClick={handleAnalyze}
      disabled={!activeSessionId || agentStreaming}
      size="sm"
      variant="default"
    >
      {agentStreaming ? "Analyzing..." : "Analyze Session"}
    </Button>
  );
}
