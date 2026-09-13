"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/client";
import { useUpdateRow } from "../hooks";
import type { ItemRow, ItemValue, ItemValueUpdate } from "../api";

const TEXT_FIELDS = ["item_name", "model_no", "quantity", "unit"] as const;
const REQUIRED = ["item_name", "model_no", "quantity", "unit", "due_date"];

type Draft = {
  values: Record<string, { text: string; needsConfirmation: boolean }>;
  dueKind: "fixed_date" | "month_range";
  dueStart: string;
  dueEnd: string;
  dueNeedsConfirmation: boolean;
};

function initialDraft(row: ItemRow): Draft {
  const values: Draft["values"] = {};
  for (const field of [...TEXT_FIELDS, "note"]) {
    const value = row.values[field];
    values[field] = {
      text: value?.value_text ?? "",
      needsConfirmation: value?.state === "needs_confirmation",
    };
  }
  const due = row.values.due_date;
  return {
    values,
    dueKind: due?.due_kind === "month_range" ? "month_range" : "fixed_date",
    dueStart: due?.due_start ?? "",
    dueEnd: due?.due_end ?? "",
    dueNeedsConfirmation: due?.state === "needs_confirmation",
  };
}

/** SCR-07 行の修正。原文は編集できない形で見せ、直せるのは値だけ。 */
export function RowEditDialog({
  inquiryId,
  row,
  onClose,
}: {
  inquiryId: string;
  row: ItemRow;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Draft>(() => initialDraft(row));
  const update = useUpdateRow(inquiryId, onClose);
  const error = update.error instanceof ApiError ? update.error : null;

  const setValue = (field: string, patch: Partial<Draft["values"][string]>) =>
    setDraft((d) => ({
      ...d,
      values: { ...d.values, [field]: { ...d.values[field], ...patch } },
    }));

  const submit = () => {
    const values: Record<string, ItemValueUpdate> = {};
    for (const field of [...TEXT_FIELDS, "note"]) {
      const entry = draft.values[field];
      values[field] = entry.needsConfirmation
        ? { state: "needs_confirmation" }
        : { state: "extracted", value: entry.text };
    }
    values.due_date = draft.dueNeedsConfirmation
      ? { state: "needs_confirmation" }
      : {
          state: "extracted",
          kind: draft.dueKind,
          start_date: draft.dueStart,
          end_date: draft.dueKind === "month_range" ? draft.dueEnd : undefined,
        };
    update.mutate({ rowId: row.row_id, values });
  };

  const raw = (field: string): ItemValue | undefined => row.values[field];

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="dialog" role="dialog" aria-modal="true">
        <div className="inline-row">
          <h2>{t("edit.title", { row: row.row_no })}</h2>
          <span className="close" onClick={onClose} role="button" tabIndex={0}>
            {t("source.close")}
          </span>
        </div>
        <p className="meta">{t("edit.lead")}</p>

        <div className="grid-2" style={{ marginTop: 12 }}>
          {TEXT_FIELDS.map((field) => (
            <div className="field" key={field}>
              <label htmlFor={`edit-${field}`}>
                {t(`items.columns.${field}`)}
                {REQUIRED.includes(field) ? t("edit.required") : null}
              </label>
              <input
                id={`edit-${field}`}
                className="input"
                value={draft.values[field].text}
                disabled={draft.values[field].needsConfirmation}
                onChange={(e) => setValue(field, { text: e.target.value })}
              />
              <label className="hint">
                <input
                  type="checkbox"
                  checked={draft.values[field].needsConfirmation}
                  onChange={(e) =>
                    setValue(field, { needsConfirmation: e.target.checked })
                  }
                />{" "}
                {/* ラベルに項目名を入れる。項目が並ぶ中で「要確認にする」とだけ書くと、
                    隣の項目に当ててしまう（⑥ TEST-05 の 2026-09-13 の計測で発生） */}
                {t("edit.markNeedsConfirmationOf", {
                  field: t(`items.columns.${field}`),
                })}
              </label>
              {raw(field)?.raw_text ? (
                <span className="orig">
                  {t("source.raw")}: {raw(field)?.raw_text}
                  {raw(field)?.source
                    ? `　${raw(field)?.source?.input_name} ${raw(field)?.source?.locator_label}`
                    : ""}
                </span>
              ) : null}
            </div>
          ))}
        </div>

        <div className="field">
          <label>
            {t("items.columns.due_date")}
            {t("edit.required")}
          </label>
          <div className="radio-row">
            <label>
              <input
                type="radio"
                name="due-kind"
                checked={
                  !draft.dueNeedsConfirmation && draft.dueKind === "fixed_date"
                }
                onChange={() =>
                  setDraft((d) => ({
                    ...d,
                    dueKind: "fixed_date",
                    dueNeedsConfirmation: false,
                  }))
                }
              />{" "}
              {t("edit.dueFixed")}
            </label>
            <label>
              <input
                type="radio"
                name="due-kind"
                checked={
                  !draft.dueNeedsConfirmation && draft.dueKind === "month_range"
                }
                onChange={() =>
                  setDraft((d) => ({
                    ...d,
                    dueKind: "month_range",
                    dueNeedsConfirmation: false,
                  }))
                }
              />{" "}
              {t("edit.dueMonthRange")}
            </label>
            <label>
              <input
                type="radio"
                name="due-kind"
                checked={draft.dueNeedsConfirmation}
                onChange={() =>
                  setDraft((d) => ({ ...d, dueNeedsConfirmation: true }))
                }
              />{" "}
              {t("edit.dueNeedsConfirmation")}
            </label>
          </div>
          {draft.dueNeedsConfirmation ? null : (
            <div className="inline-row">
              <input
                type="date"
                className="input"
                value={draft.dueStart}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, dueStart: e.target.value }))
                }
              />
              {draft.dueKind === "month_range" ? (
                <>
                  <span className="meta">〜</span>
                  <input
                    type="date"
                    className="input"
                    value={draft.dueEnd}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, dueEnd: e.target.value }))
                    }
                  />
                </>
              ) : null}
            </div>
          )}
          {raw("due_date")?.raw_text ? (
            <span className="orig">
              {t("source.raw")}: {raw("due_date")?.raw_text}
            </span>
          ) : null}
        </div>

        <div className="field">
          <label htmlFor="edit-note">{t("items.columns.note")}</label>
          <input
            id="edit-note"
            className="input"
            value={draft.values.note.text}
            onChange={(e) => setValue("note", { text: e.target.value })}
          />
        </div>

        {error ? (
          <p className="error-text">
            {t(`edit.errors.${error.code}`, { defaultValue: error.message })}
          </p>
        ) : null}

        <div className="actions">
          <span className="sub">{t("edit.savedRowIsChecked")}</span>
          <div className="spacer" />
          <button className="btn" onClick={onClose} disabled={update.isPending}>
            {t("confirm.back")}
          </button>
          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={update.isPending}
          >
            {update.isPending ? t("edit.saving") : t("edit.save")}
          </button>
        </div>
      </div>
    </>
  );
}
