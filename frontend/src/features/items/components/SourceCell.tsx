"use client";

import type { ItemRow } from "../api";

const FIELDS = [
  "item_name",
  "model_no",
  "quantity",
  "unit",
  "due_date",
  "note",
];

/** 行がどの入力から来たか（③ SCR-05 の読み取り元の列）。位置は値ごとのセルに出す。 */
export function SourceCell({ row }: { row: ItemRow }) {
  const names = new Set<string>();
  for (const field of FIELDS) {
    const source = row.values[field]?.source;
    if (source) names.add(source.input_name);
  }
  return (
    <td>
      {[...names].map((name) => (
        <span key={name} className="src-badge" style={{ marginRight: 4 }}>
          {name}
        </span>
      ))}
    </td>
  );
}
