/**
 * Haupt-Layout: 3-Spalten-Anordnung mit veraenderbaren Panel-Breiten
 * Nutzt shadcn ResizablePanelGroup fuer flexible Aufteilung
 */
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { LeftPanel } from "./LeftPanel";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";

/** Haupt-App-Rahmen mit 3 veraenderbaren Spalten */
export function AppShell() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <ResizablePanelGroup direction="horizontal">
        {/* Linke Spalte: Session-Liste */}
        <ResizablePanel defaultSize={15} minSize={10} maxSize={25}>
          <LeftPanel />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Mittlere Spalte: Upload und AI-Chat */}
        <ResizablePanel defaultSize={40} minSize={25}>
          <CenterPanel />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Rechte Spalte: Assets und Bericht */}
        <ResizablePanel defaultSize={45} minSize={30}>
          <RightPanel />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
