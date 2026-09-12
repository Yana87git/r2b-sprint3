"use client";

import { useTranslation } from "react-i18next";
import { useRouter } from "next/navigation";
import { ApiError } from "@/shared/api/client";
import { useConfirmInquiry } from "../hooks";
import type { ItemList } from "../api";

type Props = { data: ItemList; onClose: () => void };

/** 確定の確認ダイアログ（③ SCR-05）。確定したら SCR-09 へ。 */
export function ConfirmDialog({ data, onClose }: Props) {
  const { t } = useTranslation();
  const router = useRouter();
  const confirm = useConfirmInquiry(data.inquiry_id, () =>
    router.push(`/inquiries/${data.inquiry_id}/done`),
  );

  const needsConfirmation =
    data.summary.by_classification.needs_confirmation ?? 0;
  const error = confirm.error instanceof ApiError ? confirm.error : null;

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="dialog" role="dialog" aria-modal="true">
        <h2 style={{ marginBottom: 10 }}>{t("confirm.title")}</h2>
        <p>{t("confirm.lead")}</p>
        <p style={{ marginTop: 6 }}>
          {t("confirm.counts", {
            pending: needsConfirmation,
            excluded: data.summary.excluded_rows,
          })}
        </p>
        {error ? (
          <p className="error-text" style={{ marginTop: 10 }}>
            {t(`confirm.errors.${error.code}`, { defaultValue: error.message })}
          </p>
        ) : null}
        <div className="actions">
          <div className="spacer" />
          <button
            className="btn"
            onClick={onClose}
            disabled={confirm.isPending}
          >
            {t("confirm.back")}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => confirm.mutate()}
            disabled={confirm.isPending}
          >
            {confirm.isPending ? t("confirm.working") : t("confirm.submit")}
          </button>
        </div>
      </div>
    </>
  );
}
