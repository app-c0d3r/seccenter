/**
 * Asset-Tabelle: Zeigt alle IOCs der aktiven Session mit Status-Verwaltung
 * Nutzt TanStack Table fuer Sortierung und effizientes Rendering
 */
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { useSessionStore } from "@/store/sessionStore";
import { apiClient } from "@/api/apiClient";
import type { AnalyzedAsset, AssetStatus } from "@/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const columnHelper = createColumnHelper<AnalyzedAsset>();

/** Asset-Tabellen-Komponente mit TanStack Table und Status-Dropdown */
export function AssetTable() {
  const [sorting, setSorting] = useState<SortingState>([]);

  const { activeSessionId, sessions, updateAssetStatus } = useSessionStore((state) => ({
    activeSessionId: state.activeSessionId,
    sessions: state.sessions,
    updateAssetStatus: state.updateAssetStatus,
  }));

  // Assets der aktiven Session ermitteln
  const assets: AnalyzedAsset[] =
    activeSessionId && sessions[activeSessionId]
      ? sessions[activeSessionId].assets
      : [];

  /** Status-Aenderung an Backend und Store melden */
  async function handleStatusChange(
    sessionId: string,
    assetId: string,
    newStatus: AssetStatus
  ) {
    try {
      await apiClient.updateAssetStatus(sessionId, assetId, newStatus);
      updateAssetStatus(sessionId, assetId, newStatus);
    } catch (error: unknown) {
      console.error("Status-Aktualisierung fehlgeschlagen:", error);
    }
  }

  const columns = [
    // Wert des Assets (IP, Domain, Hash) in Monospace-Schrift
    columnHelper.accessor("value", {
      header: "Value",
      cell: (info) => (
        <span className="font-mono text-xs">{info.getValue()}</span>
      ),
    }),
    // Typ-Badge des Assets
    columnHelper.accessor("type", {
      header: "Type",
      cell: (info) => (
        <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
          {info.getValue()}
        </span>
      ),
    }),
    // Status-Dropdown fuer direkte Aenderung
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => {
        const asset = info.row.original;
        const sessionId = activeSessionId ?? "";
        return (
          <Select
            value={asset.status}
            onValueChange={(value: string) =>
              void handleStatusChange(sessionId, asset.id, value as AssetStatus)
            }
          >
            <SelectTrigger className="h-7 w-32 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="PENDING">PENDING</SelectItem>
              <SelectItem value="CONFIRMED">CONFIRMED</SelectItem>
              <SelectItem value="IGNORED">IGNORED</SelectItem>
            </SelectContent>
          </Select>
        );
      },
    }),
    // Erstellungszeit des Assets
    columnHelper.accessor("created_at", {
      header: "Time",
      cell: (info) => (
        <span className="text-xs text-muted-foreground">
          {new Date(info.getValue()).toLocaleTimeString()}
        </span>
      ),
    }),
  ];

  const table = useReactTable({
    data: assets,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // Leerzustand wenn keine Assets vorhanden
  if (assets.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Upload a file to extract assets
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={header.column.getCanSort() ? "cursor-pointer select-none" : ""}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {/* Sortierrichtungs-Indikator */}
                  {header.column.getIsSorted() === "asc" && " ↑"}
                  {header.column.getIsSorted() === "desc" && " ↓"}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
