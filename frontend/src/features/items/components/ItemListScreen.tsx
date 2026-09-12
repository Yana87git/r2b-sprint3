"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import { useCheckRow, useItems } from "../hooks";
import type { Classification, ItemRow } from "../api";
import { ItemRowLine } from "./ItemRowLine";
import { ConfirmDialog } from "./ConfirmDialog";

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
  const canConfirm =
    summary.unchecked_rows === 0 && summary.unreadable_input_count === 0;

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
              input.status === "unreadable" ? "file-chip is-error" : "file-chip"
            }
          >
            {input.display_name}
            {input.status === "unreadable" ? (
              <span className="error-text">
                {t(`unreadable.${input.unreadable_reason ?? "illegible"}`)}
              </span>
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
      </div>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("items.columns.check")}</th>
                <th>{t("items.columns.classification")}</th>
                <th>{t("items.columns.no")}</th>
                <th>{t("items.columns.itemName")}</th>
                <th>{t("items.columns.modelNo")}</th>
                <th className="num">{t("items.columns.quantity")}</th>
                <th>{t("items.columns.unit")}</th>
                <th>{t("items.columns.dueDate")}</th>
                <th>{t("items.columns.note")}</th>
                <th>{t("items.columns.source")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {GROUPS.map(({ key, classifications }) => {
                const groupRows = group(classifications);
                if (groupRows.length === 0) return null;
                return (
                  <>
                    <tr className="group-row" key={key}>
                      <td colSpan={11}>
                        {t(`items.groups.${key}`, { n: groupRows.length })}
                      </td>
                    </tr>
                    {groupRows.map((row) => (
                      <ItemRowLine
                        key={row.row_id}
                        row={row}
                        onCheck={(rowId) => check.mutate(rowId)}
                        disabled={check.isPending}
                      />
                    ))}
                  </>
                );
              })}
              {excluded.length > 0 ? (
                <>
                  <tr className="group-row">
                    <td colSpan={11}>{t("items.groups.excluded")}</td>
                  </tr>
                  {excluded.map((row) => (
                    <ItemRowLine
                      key={row.row_id}
                      row={row}
                      onCheck={(rowId) => check.mutate(rowId)}
                      disabled
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

      {confirming ? (
        <ConfirmDialog data={data} onClose={() => setConfirming(false)} />
      ) : null}
    </>
  );
}
