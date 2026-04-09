/**
 * Editable report canvas for AI-generated threat reports.
 * Renders {header, body, foot} sections with inline editing.
 * All edits update the Zustand store via patchReportSection.
 */
import { useCallback } from "react";
import { useSessionStore } from "@/store/sessionStore";
import type {
  ReportDraft,
  ReportHeader,
  AssetSummaryItem,
} from "@/types/agent";

export function ReportCanvas() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const draft = useSessionStore((s) =>
    s.activeSessionId ? s.reportDraft[s.activeSessionId] : undefined,
  );
  const patchReportSection = useSessionStore((s) => s.patchReportSection);

  const updateHeader = useCallback(
    (field: keyof ReportHeader, value: string) => {
      if (!activeSessionId || !draft) return;
      patchReportSection(activeSessionId, "header", {
        ...draft.header,
        [field]: value,
      });
    },
    [activeSessionId, draft, patchReportSection],
  );

  const updateFinding = useCallback(
    (index: number, value: string) => {
      if (!activeSessionId || !draft) return;
      const updated = draft.body.assets_summary.map(
        (item: AssetSummaryItem, i: number) =>
          i === index ? { ...item, findings: value } : item,
      );
      patchReportSection(activeSessionId, "body", {
        assets_summary: updated,
      });
    },
    [activeSessionId, draft, patchReportSection],
  );

  const updateConclusion = useCallback(
    (value: string) => {
      if (!activeSessionId || !draft) return;
      patchReportSection(activeSessionId, "foot", {
        ...draft.foot,
        conclusion: value,
      });
    },
    [activeSessionId, draft, patchReportSection],
  );

  const updateListField = useCallback(
    (field: "next_steps" | "tips_and_measures", value: string) => {
      if (!activeSessionId || !draft) return;
      const items = value
        .split("\n")
        .filter((line: string) => line.trim() !== "");
      patchReportSection(activeSessionId, "foot", {
        ...draft.foot,
        [field]: items,
      });
    },
    [activeSessionId, draft, patchReportSection],
  );

  /* Shared CSS for inline-editable inputs */
  const inputClass =
    "rounded border-transparent bg-transparent px-1 hover:border-border " +
    "focus:border-ring focus:outline-none";

  // Empty state — no draft or draft has no meaningful content
  if (!draft || !hasContent(draft)) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-muted-foreground/30 p-8">
        <p className="text-sm text-muted-foreground">
          Click &quot;Analyze Session&quot; to generate a report
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-2">
      {/* Header Section */}
      <section className="rounded-lg border p-3">
        <SectionHeading>Header</SectionHeading>
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          {(["what", "when", "who"] as const).map((field) => (
            <HeaderField
              key={field}
              label={field}
              value={draft.header[field]}
              inputClass={inputClass}
              onChange={(v) => updateHeader(field, v)}
            />
          ))}
        </div>
      </section>

      {/* Body Section — Asset Findings */}
      {draft.body.assets_summary.length > 0 && (
        <section className="rounded-lg border p-3">
          <SectionHeading>Asset Findings</SectionHeading>
          <div className="space-y-2">
            {draft.body.assets_summary.map(
              (item: AssetSummaryItem, index: number) => (
                <div key={item.asset_value} className="flex gap-2 text-sm">
                  <code className="shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {item.asset_value}
                  </code>
                  <input
                    type="text"
                    value={item.findings}
                    onChange={(e) => updateFinding(index, e.target.value)}
                    className={`flex-1 ${inputClass}`}
                  />
                </div>
              ),
            )}
          </div>
        </section>
      )}

      {/* Foot — Conclusion */}
      <section className="rounded-lg border p-3">
        <SectionHeading>Conclusion</SectionHeading>
        <textarea
          value={draft.foot.conclusion}
          onChange={(e) => updateConclusion(e.target.value)}
          rows={3}
          className={`w-full resize-none text-sm ${inputClass}`}
        />
      </section>

      {/* Foot — Next Steps */}
      <section className="rounded-lg border p-3">
        <SectionHeading>Next Steps</SectionHeading>
        <textarea
          value={draft.foot.next_steps.join("\n")}
          onChange={(e) => updateListField("next_steps", e.target.value)}
          rows={Math.max(2, draft.foot.next_steps.length)}
          placeholder="One step per line"
          className={`w-full resize-none text-sm ${inputClass}`}
        />
      </section>

      {/* Foot — Tips & Measures */}
      <section className="rounded-lg border p-3">
        <SectionHeading>Tips &amp; Measures</SectionHeading>
        <textarea
          value={draft.foot.tips_and_measures.join("\n")}
          onChange={(e) => updateListField("tips_and_measures", e.target.value)}
          rows={Math.max(2, draft.foot.tips_and_measures.length)}
          placeholder="One tip per line"
          className={`w-full resize-none text-sm ${inputClass}`}
        />
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Small helper components                                            */
/* ------------------------------------------------------------------ */

/** Consistent section heading used across all report sections */
function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </h3>
  );
}

/** Single label + input row inside the header grid */
function HeaderField({
  label,
  value,
  inputClass,
  onChange,
}: {
  label: string;
  value: string;
  inputClass: string;
  onChange: (v: string) => void;
}) {
  return (
    <>
      <span className="font-medium capitalize text-muted-foreground">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      />
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Utility                                                            */
/* ------------------------------------------------------------------ */

/** Check if a report draft has any meaningful content */
function hasContent(draft: ReportDraft): boolean {
  return (
    draft.header.what !== "" ||
    draft.body.assets_summary.length > 0 ||
    draft.foot.conclusion !== ""
  );
}
