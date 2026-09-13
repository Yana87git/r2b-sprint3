"use client";

import Link from "next/link";
import { useTranslation } from "react-i18next";
import { useItems } from "../hooks";
import type { ItemRow } from "../api";

const FIELDS = [
  "item_name",
  "model_no",
  "quantity",
  "unit",
  "due_date",
] as const;

/** 要確認の項目だけを拾う（#9 の filter=needs_confirmation と同じ考え方）。 */
function missingFields(row: ItemRow): string[] {
  return FIELDS.filter(
    (field) => row.values[field]?.state === "needs_confirmation",
  );
}

/**
 * SCR-08 要確認一覧。顧客に問い合わせる項目を1枚にまとめる。
 * 問い合わせ文面の生成（FUNC-09）は Scope 3 なので作らない。
 */
export function NeedsConfirmationScreen({ inquiryId }: { inquiryId: string }) {
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

  // 除外した行は出力されないので、問い合わせの対象にしない（⑤ #9）
  const rows = data.rows.filter(
    (row) => !row.excluded && missingFields(row).length > 0,
  );
  const itemCount = rows.reduce(
    (sum, row) => sum + missingFields(row).length,
    0,
  );

  return (
    <>
      <div className="page-head">
        <div>
          <Link
            className="btn-ghost btn"
            href={`/inquiries/${inquiryId}/items`}
          >
            {t("pending.back")}
          </Link>
          <h1>{t("pending.title")}</h1>
          <p className="meta">{data.title}</p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="panel">
          <div className="empty">{t("pending.empty")}</div>
        </div>
      ) : (
        <>
          <p style={{ marginBottom: 12 }}>
            {t("pending.count", { items: itemCount, rows: rows.length })}
          </p>
          <div className="panel">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("items.columns.no")}</th>
                    <th>{t("items.columns.itemName")}</th>
                    <th>{t("items.columns.modelNo")}</th>
                    <th>{t("pending.missing")}</th>
                    <th>{t("items.columns.source")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const names = new Set(
                      FIELDS.map(
                        (f) => row.values[f]?.source?.input_name,
                      ).filter(Boolean),
                    );
                    return (
                      <tr key={row.row_id}>
                        <td>{row.row_no}</td>
                        <td>{row.values.item_name?.value_text ?? ""}</td>
                        <td>{row.values.model_no?.value_text ?? ""}</td>
                        <td>
                          {missingFields(row)
                            .map((field) => t(`items.columns.${field}`))
                            .join("・")}
                        </td>
                        <td>
                          {[...names].map((name) => (
                            <span
                              key={name}
                              className="src-badge"
                              style={{ marginRight: 4 }}
                            >
                              {name}
                            </span>
                          ))}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <div className="panel panel-pad" style={{ marginTop: 16 }}>
        <div className="inline-row">
          <h3>{t("pending.messageTitle")}</h3>
          <span className="tag-scope3">{t("pending.scope3")}</span>
        </div>
        <p className="meta" style={{ marginTop: 6 }}>
          {t("pending.messageNote")}
        </p>
      </div>

      <div className="actions">
        <Link className="btn" href={`/inquiries/${inquiryId}/items`}>
          {t("pending.back")}
        </Link>
      </div>
    </>
  );
}
