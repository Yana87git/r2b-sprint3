"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/client";
import { originalUrl } from "../api";
import { useRerun } from "../hooks";
import { useItems } from "@/features/items/hooks";

/**
 * SCR-10 読み取り不可。理由を出し分け、**打ち切りのときだけ再実行**を出す。
 * 判読不能・明細なしは読み直しても変わらないので、原本を渡して手作業に戻す。
 */
export function UnreadableScreen({ inquiryId }: { inquiryId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { data, isPending, isError, error } = useItems(inquiryId);
  const rerun = useRerun(inquiryId, (result) =>
    router.push(`/runs/${result.run_id}`),
  );
  const rerunError = rerun.error instanceof ApiError ? rerun.error : null;

  if (isPending) return <p className="meta">{t("common.loading")}</p>;
  if (isError) return <p className="error-text">{error.message}</p>;

  if (data.status !== "unreadable") {
    return (
      <div className="panel panel-pad">
        <p>
          {t("unreadableScreen.notUnreadable", {
            status: t(`status.${data.status}`),
          })}
        </p>
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

  const reason = data.unreadable_reason ?? "illegible";
  // 打ち切り（タイムアウト・最大ターン数超過）だけ、もう一度読み直す意味がある。
  // **1回まで**という上限もサーバーが判定する（③ SCR-10「再実行しても打ち切られた」）
  const retryable = data.can_rerun;
  const retriedOut =
    !retryable && (reason === "timeout" || reason === "max_turns");
  const rows = data.rows.filter((row) => !row.excluded);

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn-ghost btn" href="/inquiries">
            {t("items.backToList")}
          </Link>
          <h1>{data.title}</h1>
          <p className="meta">
            {data.inputs.map((input) => t(`format.${input.format}`)).join("＋")}
          </p>
        </div>
      </div>

      <div
        className="banner banner-error"
        style={{ marginBottom: 16, display: "block" }}
      >
        <p className="error-text">
          {t("unreadableScreen.headline", {
            reason: t(`unreadableReason.${reason}`),
          })}
        </p>
        <p className="sub">{t(`unreadableScreen.detail.${reason}`)}</p>
      </div>

      <div className="panel panel-pad">
        <h3 style={{ marginBottom: 8 }}>{t("unreadableScreen.readSoFar")}</h3>
        {rows.length === 0 ? (
          <p className="sub">{t("unreadableScreen.nothingRead")}</p>
        ) : (
          <>
            <p className="sub" style={{ marginBottom: 10 }}>
              {t("unreadableScreen.partial", { n: rows.length })}
            </p>
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
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.row_id}>
                      <td>{row.row_no}</td>
                      <td>{row.values.item_name?.value_text ?? ""}</td>
                      <td>{row.values.model_no?.value_text ?? ""}</td>
                      <td className="num">
                        {row.values.quantity?.value_text ?? ""}
                      </td>
                      <td>{row.values.unit?.value_text ?? ""}</td>
                      <td>{row.values.due_date?.value_text ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="hint" style={{ marginTop: 8 }}>
              {t("unreadableScreen.partialHint")}
            </p>
          </>
        )}
        {retryable ? null : (
          <p style={{ marginTop: 14, fontWeight: "var(--weight-medium)" }}>
            {t(
              retriedOut
                ? "unreadableScreen.retriedFallback"
                : "unreadableScreen.fallback",
            )}
          </p>
        )}
      </div>

      <div className="panel panel-pad" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 8 }}>{t("unreadableScreen.originals")}</h3>
        <div className="files-strip">
          {data.inputs.map((input) => (
            <span key={input.input_id} className="file-chip">
              {input.display_name}
              <a
                className="btn btn-sm"
                href={originalUrl(inquiryId, input.input_id)}
                target="_blank"
                rel="noreferrer"
              >
                {t("unreadableScreen.download")}
              </a>
            </span>
          ))}
        </div>
      </div>

      {rerunError ? (
        <p className="error-text" style={{ marginTop: 12 }}>
          {rerunError.code === "RETRY_NOT_ALLOWED"
            ? t(
                `unreadableScreen.retryNotAllowed.${String(rerunError.detail.reason)}`,
                {
                  defaultValue: rerunError.message,
                },
              )
            : rerunError.message}
        </p>
      ) : null}

      <div className="actions">
        <Link className="btn" href="/inquiries">
          {t("run.backToList")}
        </Link>
        <div className="spacer" />
        {retryable ? (
          <button
            className="btn btn-primary"
            disabled={rerun.isPending}
            onClick={() => rerun.mutate()}
          >
            {rerun.isPending
              ? t("unreadableScreen.rerunning")
              : t("unreadableScreen.rerun")}
          </button>
        ) : null}
      </div>
    </>
  );
}
