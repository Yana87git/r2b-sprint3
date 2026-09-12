"use client";

import { useTranslation } from "react-i18next";
import type { ItemValue } from "../api";

/** 納期は種別と日付で表す（② FUNC-02 の (a)(b)(c)）。原文は別に見せる。 */
function dueText(value: ItemValue): string {
  if (value.due_kind === "month_range" && value.due_start && value.due_end) {
    return `${value.due_start}〜${value.due_end}`;
  }
  if (value.due_kind === "fixed_date" && value.due_start)
    return value.due_start;
  return value.value_text ?? "";
}

type Props = {
  field: string;
  value?: ItemValue;
  numeric?: boolean;
  onOpenSource?: (valueId: string) => void;
};

/** 値ひとつ分のセル。**読み取り元（ファイル名と位置）を値のすぐ下に出す**（KPI7）。 */
export function ValueCell({ field, value, numeric, onOpenSource }: Props) {
  const { t } = useTranslation();
  if (!value) return <td className={numeric ? "num" : undefined} />;
  if (value.state === "needs_confirmation") {
    return (
      <td className={numeric ? "num" : undefined}>
        <span className="val-missing">{t("items.needsConfirmation")}</span>
      </td>
    );
  }

  const normalized =
    field === "due_date" ? dueText(value) : (value.value_text ?? "");
  const raw = value.raw_text ?? "";
  const showRaw = raw !== "" && raw !== normalized;
  return (
    <td className={numeric ? "num" : undefined}>
      <div>
        <span
          className="val"
          onClick={() => value.source && onOpenSource?.(value.value_id)}
          role={value.source ? "button" : undefined}
          tabIndex={value.source ? 0 : undefined}
        >
          {normalized}
        </span>
        {value.confidence === "low" ? (
          <span className="mark-low">{t("items.low")}</span>
        ) : null}
      </div>
      {showRaw ? (
        <div className="orig">
          {t("items.raw")}: {raw}
        </div>
      ) : null}
      {value.source ? (
        <div className="orig">
          {value.source.input_name} {value.source.locator_label}
        </div>
      ) : null}
      {value.clues.map((clue) => (
        <div key={clue.clue} className="orig">
          {clue.clue} {t(`clues.${clue.clue}`)}
        </div>
      ))}
    </td>
  );
}
