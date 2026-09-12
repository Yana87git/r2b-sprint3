"use client";

import { useTranslation } from "react-i18next";
import { useValueSource } from "../hooks";

type Props = { inquiryId: string; valueId: string; onClose: () => void };

/** SCR-06 読み取り元パネル。値をクリックすると、原本の抜粋と位置が出る（KPI7）。 */
export function SourcePanel({ inquiryId, valueId, onClose }: Props) {
  const { t } = useTranslation();
  const { data, isPending, isError, error } = useValueSource(
    inquiryId,
    valueId,
  );

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" aria-label={t("source.title")}>
        <div className="inline-row">
          <h2>{t("source.title")}</h2>
          <span className="close" onClick={onClose} role="button" tabIndex={0}>
            {t("source.close")}
          </span>
        </div>

        {isPending ? <p className="meta">{t("common.loading")}</p> : null}
        {isError ? <p className="error-text">{error.message}</p> : null}

        {data ? (
          <>
            <p className="meta">
              {t("source.head", {
                row: data.row_no,
                field: t(`items.columns.${data.field}`, {
                  defaultValue: data.field,
                }),
                classification: t(
                  data.state === "needs_confirmation"
                    ? "classification.needs_confirmation"
                    : data.confidence === "low"
                      ? "classification.low_confidence"
                      : "classification.high_confidence",
                ),
              })}
            </p>

            {data.state === "needs_confirmation" ? (
              <p>
                <span className="val-missing">
                  {t("items.needsConfirmation")}
                </span>
              </p>
            ) : (
              <>
                <p style={{ fontSize: "var(--size-md)" }}>
                  <span className="meta">{t("source.raw")}</span>
                  <b style={{ fontSize: "var(--size-xl)" }}>{data.raw_text}</b>
                  {data.confidence === "low" ? (
                    <span className="mark-low">{t("items.low")}</span>
                  ) : null}
                </p>
                {data.value_text && data.value_text !== data.raw_text ? (
                  <p style={{ fontSize: "var(--size-md)" }}>
                    <span className="meta">{t("source.normalized")}</span>
                    <b>
                      {data.due_kind === "month_range"
                        ? `${data.due_start}〜${data.due_end}`
                        : data.value_text}
                    </b>
                    {data.due_kind === "month_range" ? (
                      <span className="meta">
                        　（{t("source.monthRange")}）
                      </span>
                    ) : null}
                  </p>
                ) : null}
              </>
            )}

            {data.clues.length > 0 ? (
              <p className="sub">
                {t("source.clueReason")}
                {data.clues.map((clue) => (
                  <b key={clue.clue} style={{ color: "var(--text-primary)" }}>
                    {clue.clue} {t(`clues.${clue.clue}`)}
                    {clue.detail ? (
                      <span className="meta">（{clue.detail}）</span>
                    ) : null}
                  </b>
                ))}
              </p>
            ) : null}

            {data.source ? (
              <span className="loc">
                {data.source.input_name}　{data.source.locator_label}
              </span>
            ) : null}

            {data.excerpt ? <Excerpt excerpt={data.excerpt} /> : null}

            <p className="meta">
              {t("source.sampling", {
                sampled: data.sampling.sampled_rows,
                required: data.sampling.required_samples,
              })}
            </p>
          </>
        ) : null}
      </aside>
    </>
  );
}

function Excerpt({
  excerpt,
}: {
  excerpt: NonNullable<ReturnType<typeof useValueSource>["data"]>["excerpt"];
}) {
  if (!excerpt) return null;
  if (excerpt.kind === "grid") {
    return (
      <div className="excerpt">
        <table>
          <thead>
            <tr>
              <th />
              {excerpt.columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {excerpt.rows.map((row) => (
              <tr key={row.no}>
                <th>{row.no}</th>
                {(row.cells ?? []).map((cell) => (
                  <td key={cell.col} className={cell.hit ? "hit" : undefined}>
                    {cell.text}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <div className="excerpt">
      <div className="lines">
        {excerpt.rows.map((row) => (
          <div key={row.no} className={row.hit ? "hit" : undefined}>
            <span className="no">{row.no}</span>
            <span>{row.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
