"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/client";
import { formatBytes } from "@/shared/lib/format";
import { useCreateInquiry } from "../hooks";

// ② FUNC-01・非機能。サーバー側でも同じ値で弾く（画面だけの制限にしない）
const ACCEPTED = [".xlsx", ".pdf", ".docx"];
const MAX_FILES = 10;
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const MAX_TOTAL_BYTES = 50 * 1024 * 1024;

type Judged = { file: File; ok: boolean; messageKey: string };

function judge(file: File): Judged {
  const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ACCEPTED.includes(suffix)) {
    return {
      file,
      ok: false,
      messageKey:
        suffix === ".xls" ? "intake.rejectXls" : "intake.rejectFormat",
    };
  }
  if (file.size > MAX_FILE_BYTES)
    return { file, ok: false, messageKey: "intake.rejectSize" };
  return { file, ok: true, messageKey: `intake.accept.${suffix.slice(1)}` };
}

/** SCR-03 引合書の投入。投入できたら処理状況（SCR-04）へ進む。 */
export function IntakeScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [judged, setJudged] = useState<Judged[]>([]);
  const [mailBody, setMailBody] = useState("");

  const create = useCreateInquiry((created) =>
    router.push(`/runs/${created.run_id}`),
  );

  const files = judged.map((j) => j.file);
  const hasMail = mailBody.trim().length > 0;
  const inputCount = files.length + (hasMail ? 1 : 0);
  const totalBytes = files.reduce((sum, f) => sum + f.size, 0);
  const rejected = judged.filter((j) => !j.ok);
  const tooMany = inputCount > MAX_FILES;
  const tooLarge = totalBytes > MAX_TOTAL_BYTES;
  const canSubmit =
    inputCount > 0 &&
    rejected.length === 0 &&
    !tooMany &&
    !tooLarge &&
    !create.isPending;

  const add = (list: FileList | null) => {
    if (!list) return;
    setJudged((current) => [...current, ...[...list].map(judge)]);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn-ghost btn" href="/inquiries">
            {t("intake.back")}
          </Link>
          <h1>{t("intake.title")}</h1>
          <p className="meta">{t("intake.lead")}</p>
        </div>
      </div>

      <div className="panel panel-pad">
        <div
          className={rejected.length > 0 ? "dropzone is-error" : "dropzone"}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            add(e.dataTransfer.files);
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          style={{ cursor: "pointer" }}
        >
          <strong>{t("intake.dropzone")}</strong>
          <span className="hint">{t("intake.limits")}</span>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          hidden
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />

        {tooMany || tooLarge ? (
          <p className="error-text" style={{ marginTop: 12 }}>
            {t("intake.rejectCount", {
              files: inputCount,
              size: formatBytes(totalBytes),
            })}
          </p>
        ) : null}

        {judged.length > 0 ? (
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>
                  <th>{t("intake.columns.file")}</th>
                  <th className="num">{t("intake.columns.size")}</th>
                  <th>{t("intake.columns.judgement")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {judged.map((item, index) => (
                  <tr className="file-row" key={`${item.file.name}-${index}`}>
                    <td>{item.file.name}</td>
                    <td className="num">{formatBytes(item.file.size)}</td>
                    <td className={item.ok ? undefined : "error-text"}>
                      {item.ok ? (
                        <b>{t(item.messageKey)}</b>
                      ) : (
                        t(item.messageKey, {
                          size: formatBytes(item.file.size),
                        })
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-sm"
                        onClick={() =>
                          setJudged((c) => c.filter((_, i) => i !== index))
                        }
                      >
                        {t("intake.remove")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="sub" style={{ marginTop: 12 }}>
            {t("intake.noFiles")}
          </p>
        )}

        <div className="field" style={{ marginTop: 18 }}>
          <label htmlFor="mail-body">
            {t("intake.mailBody")}
            <span className="hint">　{t("intake.mailBodyHint")}</span>
          </label>
          <textarea
            id="mail-body"
            className="input"
            value={mailBody}
            placeholder={t("intake.mailBodyPlaceholder")}
            onChange={(e) => setMailBody(e.target.value)}
          />
        </div>
        {hasMail ? (
          <div className="banner">
            <strong>{t("intake.accept.mail_body")}</strong>
            <span className="meta">
              （{t("intake.lines", { n: mailBody.trim().split("\n").length })}）
            </span>
          </div>
        ) : null}

        {create.isError ? (
          <p className="error-text" style={{ marginTop: 12 }}>
            {create.error instanceof ApiError
              ? create.error.message
              : t("common.error")}
          </p>
        ) : null}

        <div className="actions">
          <span className="sub">
            {t("intake.counted", { n: inputCount })}
            <span className="meta">　{t("intake.limitsShort")}</span>
          </span>
          {rejected.length > 0 ? (
            <span className="error-text">{t("intake.removeRejected")}</span>
          ) : null}
          <div className="spacer" />
          <Link className="btn" href="/inquiries">
            {t("intake.cancel")}
          </Link>
          <button
            className="btn btn-primary"
            disabled={!canSubmit}
            onClick={() => create.mutate({ files, mailBody })}
          >
            {create.isPending ? t("intake.submitting") : t("intake.submit")}
          </button>
        </div>
      </div>
    </>
  );
}
