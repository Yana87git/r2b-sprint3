"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { formatSubmittedAt } from "@/shared/lib/format";
import { useInquiries } from "../hooks";
import type { InquiryListItem } from "../api";

const TABS = [
  "all",
  "received",
  "reading",
  "unreadable",
  "awaiting_review",
  "confirmed",
] as const;

/** 案件の状況ごとに、行をクリックしたときの行き先を決める（③ SCR-02）。 */
function destination(inquiry: InquiryListItem): string | null {
  if (inquiry.status === "awaiting_review")
    return `/inquiries/${inquiry.inquiry_id}/items`;
  if (inquiry.status === "confirmed")
    return `/inquiries/${inquiry.inquiry_id}/done`;
  if (inquiry.status === "unreadable")
    return `/inquiries/${inquiry.inquiry_id}/unreadable`;
  if (inquiry.latest_run_id) return `/runs/${inquiry.latest_run_id}`;
  return null;
}

function statusClass(status: string): string {
  if (status === "reading") return "status status-active";
  if (status === "unreadable") return "status status-error";
  if (status === "confirmed") return "status status-done";
  return "status";
}

export function InquiryListScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const [tab, setTab] = useState<string>("all");
  const { data, isPending, isError, error, refetch } = useInquiries(
    tab === "all" ? undefined : tab,
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{t("inquiries.title")}</h1>
          <p className="meta">{t("inquiries.hint")}</p>
        </div>
        <div className="spacer" />
        <Link className="btn btn-primary" href="/inquiries/new">
          {t("inquiries.submit")}
        </Link>
      </div>

      <div className="tabs">
        {TABS.map((key) => (
          <span
            key={key}
            className={tab === key ? "on" : undefined}
            onClick={() => setTab(key)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setTab(key)}
            style={{ cursor: "pointer" }}
          >
            {key === "all" ? t("inquiries.all") : t(`status.${key}`)}
            <em>{data?.counts[key] ?? 0}</em>
          </span>
        ))}
      </div>

      {isPending ? <p className="meta">{t("common.loading")}</p> : null}
      {isError ? (
        <div className="panel panel-pad">
          <p className="error-text">{error.message}</p>
          <p className="meta">{t("items.errorHint")}</p>
          <div className="actions">
            <button className="btn" onClick={() => refetch()}>
              {t("common.retry")}
            </button>
          </div>
        </div>
      ) : null}

      {data ? (
        <div className="panel">
          {data.inquiries.length === 0 ? (
            <div className="empty">{t("inquiries.empty")}</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("inquiries.columns.submittedAt")}</th>
                    <th>{t("inquiries.columns.title")}</th>
                    <th>{t("inquiries.columns.format")}</th>
                    <th>{t("inquiries.columns.status")}</th>
                    <th>{t("inquiries.columns.supplement")}</th>
                    <th>{t("inquiries.columns.submittedBy")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.inquiries.map((inquiry) => {
                    const href = destination(inquiry);
                    return (
                      <tr
                        key={inquiry.inquiry_id}
                        className={href ? "clickable" : undefined}
                        onClick={() => href && router.push(href)}
                      >
                        <td>{formatSubmittedAt(inquiry.submitted_at)}</td>
                        <td>{inquiry.title}</td>
                        <td>
                          {inquiry.formats
                            .map((f) => t(`format.${f}`))
                            .join("＋") || "—"}
                        </td>
                        <td>
                          <span className={statusClass(inquiry.status)}>
                            {t(`status.${inquiry.status}`)}
                          </span>
                        </td>
                        <td
                          className={
                            inquiry.status === "unreadable" ? undefined : "meta"
                          }
                        >
                          <Supplement inquiry={inquiry} />
                        </td>
                        <td>{inquiry.submitted_by_name}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
    </>
  );
}

/** 補足の列は状況ごとに出し分ける（③ SCR-02）。 */
function Supplement({ inquiry }: { inquiry: InquiryListItem }) {
  const { t } = useTranslation();
  if (inquiry.status === "unreadable") {
    return (
      <span className="error-text">
        {t(`unreadableReason.${inquiry.unreadable_reason ?? "illegible"}`)}
      </span>
    );
  }
  if (inquiry.status === "awaiting_review") {
    return (
      <>
        {t("inquiries.uncheckedOf", {
          unchecked: inquiry.unchecked_rows,
          total: inquiry.total_rows,
        })}
        {inquiry.unreadable_input_count > 0
          ? t("inquiries.andUnreadableInputs", {
              n: inquiry.unreadable_input_count,
            })
          : ""}
      </>
    );
  }
  if (inquiry.status === "confirmed" && inquiry.pending_row_count) {
    return <>{t("inquiries.pendingRows", { n: inquiry.pending_row_count })}</>;
  }
  if (inquiry.status === "reading") return <>{t("inquiries.reading")}</>;
  return <>—</>;
}
