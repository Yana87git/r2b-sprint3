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
  confirmed_at: string | null;
  confirmed_by_name: string | null;
  pending_row_count: number | null;
  export_row_count: number | null;
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

export type ConfirmResult = {
  inquiry_id: string;
  confirmed_at: string;
  row_count: number;
  pending_row_count: number;
  download_path: string;
};

/** ⑤ #17。409 のときは ApiError の code で理由が分かる。 */
export function confirmInquiry(inquiryId: string): Promise<ConfirmResult> {
  return postJson<ConfirmResult>(`/api/v1/inquiries/${inquiryId}/confirm`);
}

/** ⑤ #18。出力済み Excel の URL（ブラウザにそのまま開かせる）。 */
export function exportUrl(inquiryId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return `${base}/api/v1/inquiries/${inquiryId}/export`;
}

export type ExcerptCell = { col: string; text: string; hit: boolean };

export type ExcerptRow = {
  no: number;
  text?: string | null;
  hit?: boolean | null;
  locator?: string | null;
  cells?: ExcerptCell[] | null;
};

export type Excerpt = {
  kind: "grid" | "lines";
  columns: string[];
  rows: ExcerptRow[];
};

export type ValueSourceDetail = {
  value_id: string;
  row_id: string;
  row_no: number;
  field: string;
  state: "extracted" | "needs_confirmation";
  confidence: "high" | "low";
  raw_text: string | null;
  value_text: string | null;
  due_kind: string | null;
  due_start: string | null;
  due_end: string | null;
  clues: ValueClue[];
  source: {
    input_id: string;
    input_name: string;
    format: string;
    locator_label: string;
  } | null;
  excerpt: Excerpt | null;
  sampling: {
    sampled_rows: number;
    required_samples: number;
    confident_rows: number;
    opened_now: boolean;
  };
};

/** ⑤ #14。**開いた事実が抜き取りとして記録される**（確信が高い行は1回だけ）。 */
export function fetchValueSource(
  inquiryId: string,
  valueId: string,
): Promise<ValueSourceDetail> {
  return request<ValueSourceDetail>(
    `/api/v1/inquiries/${inquiryId}/values/${valueId}/source`,
  );
}

export type BulkCheckResult = { checked_rows: number; summary: ItemSummary };

/** ⑤ #12。抜き取りが足りなければ 409 SAMPLING_NOT_ENOUGH。 */
export function bulkCheck(inquiryId: string): Promise<BulkCheckResult> {
  return postJson<BulkCheckResult>(
    `/api/v1/inquiries/${inquiryId}/items/bulk-check`,
  );
}

export type InputExclusion = {
  input_id: string;
  display_name: string;
  status: string;
  unreadable_reason: string | null;
  excluded: boolean;
};

/** ⑤ #15。読み取れなかった入力を除外する／取り消す。 */
export function excludeInput(
  inquiryId: string,
  inputId: string,
  excluded: boolean,
): Promise<InputExclusion> {
  return request<InputExclusion>(
    `/api/v1/inquiries/${inquiryId}/inputs/${inputId}/exclusion`,
    { method: excluded ? "POST" : "DELETE" },
  );
}

export type ItemValueUpdate = {
  state?: "extracted" | "needs_confirmation";
  value?: string;
  kind?: "fixed_date" | "month_range";
  start_date?: string;
  end_date?: string;
};

export type RowUpdateResult = {
  row_id: string;
  row_no: number;
  classification: Classification;
  check_state: string;
  edited_fields: string[];
};

/** ⑤ #10。直すとその行は確認済みになる。 */
export function updateRow(
  inquiryId: string,
  rowId: string,
  values: Record<string, ItemValueUpdate>,
): Promise<RowUpdateResult> {
  return request<RowUpdateResult>(
    `/api/v1/inquiries/${inquiryId}/items/${rowId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    },
  );
}
