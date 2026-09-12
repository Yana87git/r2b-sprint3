import { render, screen } from "@testing-library/react";
import "@/shared/i18n";
import { ValueCell } from "../ValueCell";
import type { ItemValue } from "../../api";

const base: ItemValue = {
  value_id: "v1",
  state: "extracted",
  confidence: "high",
  raw_text: "10月末",
  value_text: "2026-10-21〜2026-10-31",
  quantity_value: null,
  due_kind: "month_range",
  due_start: "2026-10-21",
  due_end: "2026-10-31",
  source: {
    input_id: "i1",
    input_name: "見積依頼.xlsx",
    locator: null,
    locator_label: "明細!F13",
  },
  clues: [],
};

function renderCell(value: ItemValue) {
  return render(
    <table>
      <tbody>
        <tr>
          <ValueCell field="due_date" value={value} />
        </tr>
      </tbody>
    </table>,
  );
}

describe("ValueCell", () => {
  it("正規化後の値と原文の両方を出し、読み取り元を値の下に置く", () => {
    renderCell(base);
    expect(screen.getByText("2026-10-21〜2026-10-31")).toBeInTheDocument();
    expect(screen.getByText(/原文: 10月末/)).toBeInTheDocument();
    expect(screen.getByText(/見積依頼.xlsx 明細!F13/)).toBeInTheDocument();
  });

  it("確信が低い値には印と手がかりを出す", () => {
    renderCell({
      ...base,
      confidence: "low",
      clues: [{ clue: "H2", detail: null }],
    });
    expect(screen.getByText("低")).toBeInTheDocument();
    expect(screen.getByText(/H2 列内の形式ずれ/)).toBeInTheDocument();
  });

  it("要確認の値は「要確認」とだけ出す（読み取り元は無い）", () => {
    renderCell({
      ...base,
      state: "needs_confirmation",
      raw_text: null,
      value_text: null,
      source: null,
    });
    expect(screen.getByText("要確認")).toBeInTheDocument();
    expect(screen.queryByText(/明細!/)).not.toBeInTheDocument();
  });
});
