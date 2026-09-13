"use client";

import { useTranslation } from "react-i18next";
import type { ItemRow } from "../api";
import { SourceCell } from "./SourceCell";
import { ValueCell } from "./ValueCell";

type Props = {
  row: ItemRow;
  onToggleCheck: (rowId: string, checked: boolean) => void;
  disabled: boolean;
  onOpenSource?: (valueId: string) => void;
  onEdit?: (row: ItemRow) => void;
};

/**
 * 品目リスト案の1行。
 * 確認はチェックボックス（外せる）。**確認済みの行は左端に帯を出す** —
 * チェックだけだと、一覧でどこまで進んだかが見えないため（③ SCR-05）。
 */
export function ItemRowLine({
  row,
  onToggleCheck,
  disabled,
  onOpenSource,
  onEdit,
}: Props) {
  const { t } = useTranslation();
  const checked = row.check_state === "checked";
  const className = [
    row.excluded ? "row-excluded" : "",
    checked ? "row-checked" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={className || undefined}>
      <td className="check">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled || row.excluded}
          aria-label={t("items.check")}
          onChange={(e) => onToggleCheck(row.row_id, e.target.checked)}
        />
      </td>
      <td>
        {onEdit && !row.excluded ? (
          <button className="btn btn-sm" onClick={() => onEdit(row)}>
            {t("items.edit")}
          </button>
        ) : null}
      </td>
      <td className="cls">{t(`classification.${row.classification}`)}</td>
      <td>{row.row_no}</td>
      <ValueCell
        field="item_name"
        value={row.values.item_name}
        onOpenSource={onOpenSource}
      />
      <ValueCell
        field="model_no"
        value={row.values.model_no}
        onOpenSource={onOpenSource}
      />
      <ValueCell
        field="quantity"
        value={row.values.quantity}
        onOpenSource={onOpenSource}
        numeric
      />
      <ValueCell
        field="unit"
        value={row.values.unit}
        onOpenSource={onOpenSource}
      />
      <ValueCell
        field="due_date"
        value={row.values.due_date}
        onOpenSource={onOpenSource}
      />
      <ValueCell
        field="note"
        value={row.values.note}
        onOpenSource={onOpenSource}
      />
      <SourceCell row={row} />
    </tr>
  );
}
