/**
 * Chat panel for AI agent conversation
 * Streams responses via SSE and updates Zustand store
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ChatMessage } from "@/components/ChatMessage";
import { streamChat } from "@/api/sseClient";
import { useSessionStore } from "@/store/sessionStore";
import { EMPTY_REPORT_DRAFT } from "@/types/agent";

export function ChatPanel() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const chatMessages = useSessionStore((s) =>
    s.activeSessionId ? (s.chatMessages[s.activeSessionId] ?? []) : [],
  );
  const reportDraft = useSessionStore((s) =>
    s.activeSessionId
      ? (s.reportDraft[s.activeSessionId] ?? EMPTY_REPORT_DRAFT)
      : EMPTY_REPORT_DRAFT,
  );
  const agentStreaming = useSessionStore((s) => s.agentStreaming);
  const addChatMessage = useSessionStore((s) => s.addChatMessage);
  const appendToLastAssistantMessage = useSessionStore(
    (s) => s.appendToLastAssistantMessage,
  );
  const setReportDraft = useSessionStore((s) => s.setReportDraft);
  const patchReportSection = useSessionStore((s) => s.patchReportSection);
  const setAgentStreaming = useSessionStore((s) => s.setAgentStreaming);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSend = useCallback(async () => {
    if (!activeSessionId || !input.trim() || agentStreaming) return;

    const userMessage = input.trim();
    setInput("");

    // Add user message to store
    addChatMessage(activeSessionId, {
      id: crypto.randomUUID(),
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
    });

    // Add empty assistant message for streaming
    addChatMessage(activeSessionId, {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    });

    setAgentStreaming(true);
    abortRef.current = new AbortController();

    try {
      await streamChat(
        activeSessionId,
        userMessage,
        reportDraft,
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
    input,
    agentStreaming,
    reportDraft,
    addChatMessage,
    appendToLastAssistantMessage,
    setReportDraft,
    patchReportSection,
    setAgentStreaming,
  ]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!activeSessionId) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Select a session to start chatting
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Message list */}
      <div className="flex-1 space-y-3 overflow-y-auto p-2">
        {chatMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              Send a message or click Analyze Session
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t p-2">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the analysis..."
            disabled={agentStreaming}
            rows={2}
            className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
          />
          <Button
            onClick={handleSend}
            disabled={agentStreaming || !input.trim()}
            size="sm"
            className="self-end"
          >
            {agentStreaming ? "..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}
