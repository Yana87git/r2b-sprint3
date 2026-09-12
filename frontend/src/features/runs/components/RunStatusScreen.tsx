"use client";

import Link from "next/link";
import { useTranslation } from "react-i18next";
import { useRun } from "../hooks";
import type { RunStatus } from "../api";

const STEPS = ["received", "reading", "awaiting_review", "confirmed"] as const;

function stepClass(step: string, run: RunStatus): string {
  const status = run.status ?? "received";
  if (status === "unreadable") {
    // 読み取り不可は「読み取り中」の位置に出す（③ SCR-04）
    if (step === "received") return "step done";
    if (step === "reading") return "step fail";
    return "step";
  }
  const current = STEPS.indexOf(status as (typeof STEPS)[number]);
  const index = STEPS.indexOf(step as (typeof STEPS)[number]);
  if (index < current) return "step done";
  if (index === current) return "step now";
  return "step";
}

function etaText(run: RunStatus): string {
  const minutes = Math.ceil(run.eta_seconds / 60);
  return String(minutes);
}

/** SCR-04 処理状況。#8 を3秒ごとに読み、確認待ちになったら SCR-05 へ進める。 */
export function RunStatusScreen({ runId }: { runId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError, error, refetch } = useRun(runId);

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

  const status = data.status ?? "received";
  const reading = status === "received" || status === "reading";
  const overdue = reading && data.eta_seconds === 0;

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn-ghost btn" href="/inquiries">
            {t("items.backToList")}
          </Link>
          <h1>{t("run.title")}</h1>
          <p className="meta">
            {t("run.inputsDone", {
              done: data.inputs_done,
              total: data.inputs_total,
            })}
          </p>
        </div>
      </div>

      <div className="panel panel-pad">
        <div className="stepper">
          {STEPS.map((step) => (
            <div key={step} className={stepClass(step, data)}>
              {step === "reading" && status === "unreadable"
                ? t("status.unreadable")
                : t(`status.${step}`)}
            </div>
          ))}
        </div>

        {reading ? (
          <p style={{ textAlign: "center", marginTop: 12 }}>
            {overdue ? (
              <b>{t("run.overdue")}</b>
            ) : (
              <b style={{ fontSize: "var(--size-lg)" }}>
                {t("run.eta", { n: etaText(data) })}
              </b>
            )}
            <br />
            <span className="meta">{t("run.keepsRunning")}</span>
          </p>
        ) : null}

        {status === "awaiting_review" ? (
          <p style={{ textAlign: "center", marginTop: 12 }}>
            <b>{t("run.done")}</b>
            <br />
            <span className="meta">{t("run.doneHint")}</span>
          </p>
        ) : null}

        {status === "unreadable" ? (
          <div className="banner banner-error" style={{ marginTop: 12 }}>
            <span className="error-text">
              {t("run.failed", {
                reason: t(
                  `unreadableReason.${data.unreadable_reason ?? "illegible"}`,
                ),
              })}
            </span>
          </div>
        ) : null}

        {status === "confirmed" ? (
          <p style={{ textAlign: "center", marginTop: 12 }}>
            <b>{t("status.confirmed")}</b>
          </p>
        ) : null}

        <div className="actions">
          <Link className="btn" href="/inquiries">
            {t("run.backToList")}
          </Link>
          <div className="spacer" />
          {status === "awaiting_review" ? (
            <Link
              className="btn btn-primary"
              href={`/inquiries/${data.inquiry_id}/items`}
            >
              {t("run.startReview")}
            </Link>
          ) : null}
          {status === "confirmed" ? (
            <Link
              className="btn btn-primary"
              href={`/inquiries/${data.inquiry_id}/done`}
            >
              {t("run.openResult")}
            </Link>
          ) : null}
        </div>
      </div>
    </>
  );
}
