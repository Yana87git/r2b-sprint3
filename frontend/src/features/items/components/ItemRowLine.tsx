"use client";

import { useTranslation } from "react-i18next";
import type { ItemRow } from "../api";
import { SourceCell } from "./SourceCell";
import { ValueCell } from "./ValueCell";

type Props = {
  row: ItemRow;
  onToggleCheck: (rowId: string, checked: boolean) => void;
  disabled: boolean;
  /** 抜き取りが足りていて、どの確信が高い行でも確認できる状態か */
  samplingMet?: boolean;
  onOpenSource?: (valueId: string) => void;
  onEdit?: (row: ItemRow) => void;
  onToggleExclusion?: (rowId: string, excluded: boolean) => void;
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
  samplingMet = false,
  onOpenSource,
  onEdit,
  onToggleExclusion,
}: Props) {
  const { t } = useTranslation();
  const checked = row.check_state === "checked";
  // 確信が高い行を確認できるのは (a) その行の読み取り元を開いた (b) 抜き取りが足りている
  // のどちらか（② FUNC-04）。要確認・確信が低い行はいつでも1行ずつ確認できる
  const needsSampling =
    row.classification === "high_confidence" &&
    !row.source_opened &&
    !samplingMet;
  const lockedReason =
    !checked && needsSampling ? t("items.openSourceFirst") : undefined;
  const className = [
    row.excluded ? "row-excluded" : "",
    checked ? "row-checked" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={className || undefined}>
      <td className="check" title={lockedReason}>
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled || row.excluded || Boolean(lockedReason)}
          aria-label={lockedReason ?? t("items.check")}
          onChange={(e) => onToggleCheck(row.row_id, e.target.checked)}
        />
      </td>
      <td style={{ whiteSpace: "nowrap" }}>
        {row.excluded ? (
          // 除外した行の操作は「取り消し」だけ（③ SCR-05）
          <button
            className="btn btn-sm"
            onClick={() => onToggleExclusion?.(row.row_id, false)}
          >
            {t("items.cancelExclusion")}
          </button>
        ) : (
          <>
            {onEdit ? (
              <button className="btn btn-sm" onClick={() => onEdit(row)}>
                {t("items.edit")}
              </button>
            ) : null}{" "}
            <button
              className="btn btn-sm"
              onClick={() => onToggleExclusion?.(row.row_id, true)}
            >
              {t("items.exclude")}
            </button>
          </>
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
    </tr>
  );
}
