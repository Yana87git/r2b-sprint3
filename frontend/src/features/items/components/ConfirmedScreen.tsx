"use client";

import Link from "next/link";
import { useTranslation } from "react-i18next";
import { exportUrl } from "../api";
import { useItems } from "../hooks";

const FIELDS = [
  "item_name",
  "model_no",
  "quantity",
  "unit",
  "due_date",
  "note",
] as const;

/** SCR-09 確定完了（確定済みの閲覧）。出力した内容と Excel のダウンロード。 */
export function ConfirmedScreen({ inquiryId }: { inquiryId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError, error, refetch } = useItems(inquiryId);

  if (isPending) return <p className="meta">{t("common.loading")}</p>;
  if (isError) {
    return (
      <div className="panel panel-pad">
        <p className="error-text">{error.message}</p>
        <div className="actions">
          <button className="btn" onClick={() => refetch()}>
            {t("common.retry")}
          </button>
        </div>
      </div>
    );
  }

  if (data.status !== "confirmed") {
    return (
      <div className="panel panel-pad">
        <p>{t("done.notConfirmed")}</p>
        <div className="actions">
          <Link
            className="btn btn-primary"
            href={`/inquiries/${inquiryId}/items`}
          >
            {t("done.toReview")}
          </Link>
        </div>
      </div>
    );
  }

  const rows = data.rows.filter((row) => !row.excluded);

  return (
    <>
      <div className="readonly-flag" style={{ marginBottom: 16 }}>
        <span className="stamp stamp-lg" title={t("done.stampTitle")}>
          {t("done.stamp")}
        </span>
        {t("done.readonly")}
      </div>

      <div className="page-head">
        <div>
          <Link className="btn-ghost btn" href="/inquiries">
            {t("items.backToList")}
          </Link>
          <h1>{data.title}</h1>
          <p className="meta">
            {t("done.confirmedAt", {
              at: (data.confirmed_at ?? "").slice(0, 16).replace("T", " "),
              by: data.confirmed_by_name ?? "",
            })}
            {data.pending_row_count ? (
              <b style={{ color: "var(--text-primary)" }}>
                {" ｜ "}
                {t("done.pendingRows", { n: data.pending_row_count })}
              </b>
            ) : null}
          </p>
        </div>
        <div className="spacer" />
        <div style={{ textAlign: "right" }}>
          <a
            className="btn btn-primary"
            href={exportUrl(inquiryId)}
            target="_blank"
            rel="noreferrer"
          >
            {t("done.download")}
          </a>
          <p className="hint" style={{ marginTop: 6, maxWidth: 300 }}>
            {t("done.downloadHint")}
          </p>
        </div>
      </div>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("items.columns.no")}</th>
                <th>{t("items.columns.itemName")}</th>
                <th>{t("items.columns.modelNo")}</th>
                <th className="num">{t("items.columns.quantity")}</th>
                <th>{t("items.columns.unit")}</th>
                <th>{t("items.columns.dueDate")}</th>
                <th>{t("items.columns.note")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.row_id}>
                  <td>{index + 1}</td>
                  {FIELDS.map((field) => {
                    const value = row.values[field];
                    const numeric = field === "quantity";
                    if (!value)
                      return (
                        <td
                          key={field}
                          className={numeric ? "num" : undefined}
                        />
                      );
                    if (value.state === "needs_confirmation") {
                      return (
                        <td key={field} className={numeric ? "num" : undefined}>
                          <span className="val-missing">
                            {t("done.pending")}
                          </span>
                        </td>
                      );
                    }
                    const text =
                      field === "due_date" && value.due_kind === "month_range"
                        ? `${value.due_start}〜${value.due_end}`
                        : (value.value_text ?? "");
                    return (
                      <td key={field} className={numeric ? "num" : undefined}>
                        {text}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="actions">
        <Link className="btn" href="/inquiries">
          {t("run.backToList")}
        </Link>
      </div>
    </>
  );
}
