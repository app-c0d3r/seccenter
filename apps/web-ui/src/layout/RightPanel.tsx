/**
 * Rechtes Panel: Tabs fuer Asset-Tabelle und Bericht-Platzhalter
 */
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AssetTable } from "@/components/AssetTable";

/** Rechtes Panel mit Tabs fuer Assets und Bericht */
export function RightPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden p-4">
      <Tabs defaultValue="assets" className="flex flex-1 flex-col overflow-hidden">
        <TabsList className="mb-2 w-fit">
          {/* Assets-Tab ist aktiv und zeigt die Asset-Tabelle */}
          <TabsTrigger value="assets">Assets</TabsTrigger>
          {/* Bericht-Tab ist deaktiviert – wird in Phase 2 implementiert */}
          <TabsTrigger value="report" disabled>
            Report
          </TabsTrigger>
        </TabsList>

        <TabsContent value="assets" className="flex-1 overflow-hidden">
          <AssetTable />
        </TabsContent>

        <TabsContent value="report" className="flex-1">
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-muted-foreground/30 p-8">
            <p className="text-sm text-muted-foreground">Report — Phase 2</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
