/**
 * Right panel: tabs for asset table and report canvas
 */
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AssetTable } from "@/components/AssetTable";
import { ReportCanvas } from "@/components/ReportCanvas";
import { AnalyzeButton } from "@/components/AnalyzeButton";

export function RightPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden p-4">
      {/* Header bar with action button */}
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Control Center</h2>
        <AnalyzeButton />
      </div>

      <Tabs
        defaultValue="assets"
        className="flex flex-1 flex-col overflow-hidden"
      >
        <TabsList className="mb-2 w-fit">
          <TabsTrigger value="assets">Assets</TabsTrigger>
          <TabsTrigger value="report">Report</TabsTrigger>
        </TabsList>

        <TabsContent value="assets" className="flex-1 overflow-hidden">
          <AssetTable />
        </TabsContent>

        <TabsContent value="report" className="flex-1 overflow-hidden">
          <ReportCanvas />
        </TabsContent>
      </Tabs>
    </div>
  );
}
