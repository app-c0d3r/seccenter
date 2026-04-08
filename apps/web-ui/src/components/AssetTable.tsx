/**
 * Asset table: Shows all IOCs of the active session with status management
 * Uses TanStack Table for sorting, row selection, and efficient rendering
 */
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type RowSelectionState,
} from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useSessionStore } from "@/store/sessionStore";
import { useShallow } from "zustand/react/shallow";
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
import { Button } from "@/components/ui/button";

const columnHelper = createColumnHelper<AnalyzedAsset>();

/** Asset table component with TanStack Table, row selection, and status dropdown */
export function AssetTable() {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const { activeSessionId, sessions, updateAssetStatus, markAssetsProcessing } =
    useSessionStore(
      useShallow((state) => ({
        activeSessionId: state.activeSessionId,
        sessions: state.sessions,
        updateAssetStatus: state.updateAssetStatus,
        markAssetsProcessing: state.markAssetsProcessing,
      })),
    );

  // Derive assets for the active session
  const assets: AnalyzedAsset[] =
    activeSessionId && sessions[activeSessionId]
      ? sessions[activeSessionId].assets
      : [];

  const hasProcessingAssets = assets.some((a) => a.status === "PROCESSING");

  // Poll backend every 5 seconds while assets are being processed
  useEffect(() => {
    if (!hasProcessingAssets || !activeSessionId) return;

    const intervalId = setInterval(async () => {
      try {
        const session = await apiClient.getSession(activeSessionId);
        useSessionStore
          .getState()
          .refreshSessionAssets(activeSessionId, session.assets);
      } catch (error: unknown) {
        console.error("Polling failed:", error);
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [hasProcessingAssets, activeSessionId]);

  /** Notify backend and store of a status change */
  async function handleStatusChange(
    sessionId: string,
    assetId: string,
    newStatus: AssetStatus,
  ) {
    try {
      await apiClient.updateAssetStatus(sessionId, assetId, newStatus);
      updateAssetStatus(sessionId, assetId, newStatus);
    } catch (error: unknown) {
      console.error("Status update failed:", error);
    }
  }

  const columns = [
    // Checkbox column for row selection
    columnHelper.display({
      id: "select",
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllPageRowsSelected()}
          onChange={table.getToggleAllPageRowsSelectedHandler()}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          disabled={!row.getCanSelect()}
          onChange={row.getToggleSelectedHandler()}
        />
      ),
    }),
    // Asset value (IP, domain, hash) in monospace font
    columnHelper.accessor("value", {
      header: "Value",
      cell: (info) => (
        <span className="font-mono text-xs">{info.getValue()}</span>
      ),
    }),
    // Asset type badge
    columnHelper.accessor("type", {
      header: "Type",
      cell: (info) => (
        <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
          {info.getValue()}
        </span>
      ),
    }),
    // Status dropdown for direct changes (with DLP-locked and system statuses)
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => {
        const asset = info.row.original;
        const sessionId = activeSessionId ?? "";

        // INTERNAL assets are DLP-blocked and cannot be changed by analysts
        if (asset.status === "INTERNAL") {
          return (
            <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
              INTERNAL
            </span>
          );
        }

        if (asset.status === "PROCESSING") {
          return (
            <span className="inline-flex items-center gap-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-700 border-t-transparent" />
              PROCESSING
            </span>
          );
        }

        if (asset.status === "ENRICHED") {
          return (
            <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
              ENRICHED
            </span>
          );
        }

        if (asset.status === "CRITICAL") {
          return (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-700">
              CRITICAL
            </span>
          );
        }

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
    // Asset creation time
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
    state: { sorting, rowSelection },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    enableRowSelection: (row) =>
      row.original.status === "PENDING" || row.original.status === "CONFIRMED",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // Derive selected asset IDs from row selection state
  const selectedAssetIds = Object.keys(rowSelection)
    .map((idx) => assets[Number(idx)]?.id)
    .filter(Boolean) as string[];

  /** Dispatch enrichment for selected assets and mark them as processing */
  async function handleEnrich() {
    if (!activeSessionId || selectedAssetIds.length === 0) return;
    try {
      await apiClient.enrichAssets(activeSessionId, selectedAssetIds);
      markAssetsProcessing(activeSessionId, selectedAssetIds);
      setRowSelection({});
    } catch (error: unknown) {
      console.error("Enrichment dispatch failed:", error);
    }
  }

  // Empty state when no assets are present
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
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center gap-2">
        <Button
          size="sm"
          onClick={() => void handleEnrich()}
          disabled={selectedAssetIds.length === 0}
        >
          Enrich Selected ({selectedAssetIds.length})
        </Button>
      </div>
      <div className="flex-1 overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={
                      header.column.getCanSort()
                        ? "cursor-pointer select-none"
                        : ""
                    }
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
                    {/* Sort direction indicator */}
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
    </div>
  );
}
