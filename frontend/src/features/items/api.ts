import { postJson, request } from "@/shared/api/client";

export type ValueSource = {
  input_id: string;
  input_name: string;
  locator: Record<string, unknown> | null;
  locator_label: string;
};

export type ValueClue = { clue: string; detail: string | null };

export type ItemValue = {
  value_id: string;
  state: "extracted" | "needs_confirmation";
  confidence: "high" | "low";
  raw_text: string | null;
  value_text: string | null;
  quantity_value: number | null;
  due_kind: string | null;
  due_start: string | null;
  due_end: string | null;
  source: ValueSource | null;
  clues: ValueClue[];
};

export type Classification =
  "needs_confirmation" | "low_confidence" | "high_confidence";

export type ItemRow = {
  row_id: string;
  row_no: number;
  classification: Classification;
  check_state: "unchecked" | "checked";
  excluded: boolean;
  source_opened: boolean;
  values: Partial<Record<string, ItemValue>>;
};

export type ItemSummary = {
  total_rows: number;
  excluded_rows: number;
  unchecked_rows: number;
  sampled_rows: number;
  by_classification: Partial<Record<Classification, number>>;
  unreadable_input_count: number;
};

export type InquiryInput = {
  input_id: string;
  display_name: string;
  format: string;
  status: string;
  unreadable_reason: string | null;
  row_count: number;
  excluded: boolean;
};

export type ItemList = {
  inquiry_id: string;
  title: string;
  status: string;
  review_started_at: string | null;
  inputs: InquiryInput[];
  rows: ItemRow[];
  summary: ItemSummary;
};

export type RowCheckResult = {
  row_id: string;
  check_state: string;
  checked_at: string | null;
  summary: ItemSummary;
};

/** ⑤ #9。要確認 → 確信が低い → 確信が高い の順で返る。 */
export function fetchItems(inquiryId: string): Promise<ItemList> {
  return request<ItemList>(`/api/v1/inquiries/${inquiryId}/items`);
}

/** ⑤ #11。 */
export function checkRow(
  inquiryId: string,
  rowId: string,
): Promise<RowCheckResult> {
  return postJson<RowCheckResult>(
    `/api/v1/inquiries/${inquiryId}/items/${rowId}/check`,
  );
}
