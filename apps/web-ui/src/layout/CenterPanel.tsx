/**
 * Center panel: file upload and AI chat
 */
import { UploadZone } from "@/components/UploadZone";
import { ChatPanel } from "@/components/ChatPanel";

export function CenterPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden p-4">
      <div className="shrink-0">
        <UploadZone />
      </div>
      <ChatPanel />
    </div>
  );
}
