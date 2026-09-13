"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import { ApiError } from "@/shared/api/client";
import {
  useBulkCheck,
  useCheckRow,
  useExcludeInput,
  useExcludeRow,
  useItems,
} from "../hooks";
import type { Classification, ItemRow } from "../api";
import { ItemRowLine } from "./ItemRowLine";
import { ConfirmDialog } from "./ConfirmDialog";
import { SourcePanel } from "./SourcePanel";
import { RowEditDialog } from "./RowEditDialog";

const GROUPS: { key: string; classifications: Classification[] }[] = [
  {
    key: "attention",
    classifications: ["needs_confirmation", "low_confidence"],
  },
  { key: "confident", classifications: ["high_confidence"] },
];

/** SCR-05 品目リストの確認。#9 で取り、#11 で1行ずつ確認済みにする。 */
export function ItemListScreen({ inquiryId }: { inquiryId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError, error, refetch } = useItems(inquiryId);
  const check = useCheckRow(inquiryId);
  const [confirming, setConfirming] = useState(false);
  const [openValueId, setOpenValueId] = useState<string | null>(null);
  const bulk = useBulkCheck(inquiryId);
  const exclusion = useExcludeInput(inquiryId);
  const [editing, setEditing] = useState<ItemRow | null>(null);
  const rowExclusion = useExcludeRow(inquiryId);

  if (isPending) return <p className="meta">{t("common.loading")}</p>;
  if (isError) {
    return (
      <div className="panel panel-pad">
        <p className="error-text">{error.message}</p>
        <p className="meta">{t("items.errorHint")}</p>
        <div className="actions">
          <button className="btn" onClick={() => refetch()}>
            {t("common.retry")}
          </button>
        </div>
      </div>
    );
  }

  const { summary, rows, inputs } = data;
  const active = rows.filter((row) => !row.excluded);
  const excluded = rows.filter((row) => row.excluded);
  // 未確認が残っている間は押させない。読み取れなかった入力は**サーバー側に拒否させる**
  // （409 UNREADABLE_INPUT_REMAINS を確認ダイアログに出す。除外すれば確定できる、と伝わる）
  const canConfirm = summary.unchecked_rows === 0;

  const requiredSamples = Math.min(
    3,
    summary.by_classification.high_confidence ?? 0,
  );
  const bulkError = bulk.error instanceof ApiError ? bulk.error : null;
  const checkError = check.error instanceof ApiError ? check.error : null;

  const group = (classifications: Classification[]): ItemRow[] =>
    active.filter((row) => classifications.includes(row.classification));

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn-ghost btn" href="/inquiries">
            {t("items.backToList")}
          </Link>
          <h1>{data.title}</h1>
          <p className="meta">{t(`status.${data.status}`)}</p>
        </div>
        <div className="spacer" />
        <div style={{ textAlign: "right" }}>
          <span className="meta">{t("items.uncheckedCount")}</span>
          <br />
          <b style={{ fontSize: "var(--size-xl)" }}>{summary.unchecked_rows}</b>
          <span className="sub">
            {" "}
            {t("items.ofRows", {
              total: summary.total_rows,
              excluded: summary.excluded_rows,
            })}
          </span>
        </div>
      </div>

      <p className="meta" style={{ marginBottom: 6 }}>
        {t("items.inputsLabel")}
      </p>
      <div className="files-strip">
        {inputs.map((input) => (
          <span
            key={input.input_id}
            className={
              input.status === "unreadable" && !input.excluded
                ? "file-chip is-error"
                : "file-chip"
            }
            style={input.excluded ? { opacity: 0.55 } : undefined}
          >
            {input.display_name}
            {input.status === "unreadable" ? (
              <>
                <span className={input.excluded ? "meta" : "error-text"}>
                  {input.excluded
                    ? t("items.excludedInput")
                    : t(`unreadable.${input.unreadable_reason ?? "illegible"}`)}
                </span>
                <button
                  className="btn btn-sm"
                  disabled={exclusion.isPending}
                  onClick={() =>
                    exclusion.mutate({
                      inputId: input.input_id,
                      excluded: !input.excluded,
                    })
                  }
                >
                  {input.excluded
                    ? t("items.cancelInputExclusion")
                    : t("items.excludeInput")}
                </button>
              </>
            ) : (
              <span className="meta">
                {t(`format.${input.format}`)} ｜{" "}
                {t(`inputStatus.${input.status}`, { rows: input.row_count })}
              </span>
            )}
          </span>
        ))}
      </div>

      <div className="summary">
        <span>
          {t("classification.needs_confirmation")}{" "}
          <b>{summary.by_classification.needs_confirmation ?? 0}</b>
        </span>
        <span>
          {t("classification.low_confidence")}{" "}
          <b>{summary.by_classification.low_confidence ?? 0}</b>
        </span>
        <span>
          {t("classification.high_confidence")}{" "}
          <b>{summary.by_classification.high_confidence ?? 0}</b>
        </span>
        <span className="spacer" style={{ flex: 1 }} />
        {(summary.by_classification.needs_confirmation ?? 0) > 0 ? (
          <Link className="btn btn-sm" href={`/inquiries/${inquiryId}/pending`}>
            {t("items.pendingList", {
              n: summary.by_classification.needs_confirmation ?? 0,
            })}
          </Link>
        ) : null}
      </div>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("items.columns.check")}</th>
                <th />
                <th>{t("items.columns.classification")}</th>
                <th>{t("items.columns.no")}</th>
                <th>{t("items.columns.itemName")}</th>
                <th>{t("items.columns.modelNo")}</th>
                <th className="num">{t("items.columns.quantity")}</th>
                <th>{t("items.columns.unit")}</th>
                <th>{t("items.columns.dueDate")}</th>
                <th>{t("items.columns.note")}</th>
                <th>{t("items.columns.source")}</th>
              </tr>
            </thead>
            <tbody>
              {GROUPS.map(({ key, classifications }) => {
                const groupRows = group(classifications);
                if (groupRows.length === 0) return null;
                const allChecked = groupRows.every(
                  (row) => row.check_state === "checked",
                );
                return (
                  <>
                    <tr className="group-row" key={key}>
                      {/* 全選択は確信が高い行のグループにだけ置く。
                          要確認・確信が低い行は1行ずつ確認するのが要件（② FUNC-04） */}
                      <td className="check">
                        {key === "confident" ? (
                          <input
                            type="checkbox"
                            checked={allChecked}
                            disabled={bulk.isPending || allChecked}
                            aria-label={t("items.selectAllConfident")}
                            onChange={() => bulk.mutate()}
                          />
                        ) : null}
                      </td>
                      <td colSpan={10}>
                        <span className="inline-row">
                          {t(`items.groups.${key}`, { n: groupRows.length })}
                          {key === "confident" ? (
                            <>
                              <span className="counter">
                                {t("items.sampled", {
                                  sampled: summary.sampled_rows,
                                  required: requiredSamples,
                                })}
                              </span>
                              {/* 押せないままにせず、押せて「次に何をすればいいか」を出す */}
                              <button
                                className="btn btn-sm"
                                disabled={bulk.isPending || allChecked}
                                onClick={() => bulk.mutate()}
                              >
                                {t("items.bulkCheck")}
                              </button>
                              {bulkError ? (
                                <span className="error-text">
                                  {bulkError.code === "SAMPLING_NOT_ENOUGH"
                                    ? t("items.openMoreSources", {
                                        n:
                                          Number(
                                            bulkError.detail.required_samples ??
                                              0,
                                          ) -
                                          Number(
                                            bulkError.detail.sampled_rows ?? 0,
                                          ),
                                      })
                                    : bulkError.message}
                                </span>
                              ) : null}
                            </>
                          ) : null}
                        </span>
                      </td>
                    </tr>
                    {groupRows.map((row) => (
                      <ItemRowLine
                        key={row.row_id}
                        row={row}
                        onToggleCheck={(rowId, checked) =>
                          check.mutate({ rowId, checked })
                        }
                        disabled={check.isPending}
                        samplingMet={summary.sampled_rows >= requiredSamples}
                        onOpenSource={setOpenValueId}
                        onEdit={setEditing}
                        onToggleExclusion={(rowId, excluded) =>
                          rowExclusion.mutate({ rowId, excluded })
                        }
                      />
                    ))}
                  </>
                );
              })}
              {excluded.length > 0 ? (
                <>
                  <tr className="group-row">
                    <td className="check" />
                    <td colSpan={10}>{t("items.groups.excluded")}</td>
                  </tr>
                  {excluded.map((row) => (
                    <ItemRowLine
                      key={row.row_id}
                      row={row}
                      onToggleCheck={(rowId, checked) =>
                        check.mutate({ rowId, checked })
                      }
                      disabled
                      onOpenSource={setOpenValueId}
                      onToggleExclusion={(rowId, excluded) =>
                        rowExclusion.mutate({ rowId, excluded })
                      }
                    />
                  ))}
                </>
              ) : null}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={11}>
                    <p className="empty">{t("items.empty")}</p>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div className="sticky-foot">
        <span className="sub">{t("items.footHint")}</span>
        <div className="spacer" />
        {checkError ? (
          <span className="error-text">
            {checkError.code === "SAMPLING_NOT_ENOUGH"
              ? t("items.openMoreSources", {
                  n:
                    Number(checkError.detail.required_samples ?? 0) -
                    Number(checkError.detail.sampled_rows ?? 0),
                })
              : checkError.message}
          </span>
        ) : null}
        {summary.unchecked_rows > 0 ? (
          <span className="error-text">
            {t("items.uncheckedRemain", { n: summary.unchecked_rows })}
          </span>
        ) : null}
        {summary.unreadable_input_count > 0 ? (
          <span className="error-text">
            {t("items.unreadableRemain", { n: summary.unreadable_input_count })}
          </span>
        ) : null}
        <button
          className="btn btn-primary"
          disabled={!canConfirm}
          onClick={() => setConfirming(true)}
        >
          {t("items.confirm")}
        </button>
      </div>

      {editing ? (
        <RowEditDialog
          inquiryId={inquiryId}
          row={rows.find((r) => r.row_id === editing.row_id) ?? editing}
          onClose={() => setEditing(null)}
        />
      ) : null}

      {openValueId ? (
        <SourcePanel
          inquiryId={inquiryId}
          valueId={openValueId}
          onClose={() => setOpenValueId(null)}
        />
      ) : null}

      {confirming ? (
        <ConfirmDialog data={data} onClose={() => setConfirming(false)} />
      ) : null}
    </>
  );
}
