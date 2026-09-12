"use client";

import { useTranslation } from "react-i18next";
import type { ItemRow } from "../api";
import { SourceCell } from "./SourceCell";
import { ValueCell } from "./ValueCell";

type Props = {
  row: ItemRow;
  onCheck: (rowId: string) => void;
  disabled: boolean;
  onOpenSource?: (valueId: string) => void;
  onEdit?: (row: ItemRow) => void;
};

export function ItemRowLine({
  row,
  onCheck,
  disabled,
  onOpenSource,
  onEdit,
}: Props) {
  const { t } = useTranslation();
  const checked = row.check_state === "checked";
  return (
    <tr className={row.excluded ? "row-excluded" : undefined}>
      <td className="check">
        {checked ? (
          <span className="stamp" title={t("items.checked")}>
            {t("items.stamp")}
          </span>
        ) : (
          t("items.unchecked")
        )}
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
      <td style={{ whiteSpace: "nowrap" }}>
        {checked ? null : (
          <button
            className="btn btn-sm"
            onClick={() => onCheck(row.row_id)}
            disabled={disabled}
          >
            {t("items.check")}
          </button>
        )}{" "}
        {onEdit && !row.excluded ? (
          <button className="btn btn-sm" onClick={() => onEdit(row)}>
            {t("items.edit")}
          </button>
        ) : null}
      </td>
    </tr>
  );
}
