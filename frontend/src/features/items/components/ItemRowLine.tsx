"use client";

import { useTranslation } from "react-i18next";
import type { ItemRow } from "../api";
import { SourceCell } from "./SourceCell";
import { ValueCell } from "./ValueCell";

type Props = {
  row: ItemRow;
  onCheck: (rowId: string) => void;
  disabled: boolean;
};

export function ItemRowLine({ row, onCheck, disabled }: Props) {
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
      <ValueCell field="item_name" value={row.values.item_name} />
      <ValueCell field="model_no" value={row.values.model_no} />
      <ValueCell field="quantity" value={row.values.quantity} numeric />
      <ValueCell field="unit" value={row.values.unit} />
      <ValueCell field="due_date" value={row.values.due_date} />
      <ValueCell field="note" value={row.values.note} />
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
        )}
      </td>
    </tr>
  );
}
