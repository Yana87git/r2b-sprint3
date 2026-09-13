import { postJson, request } from "@/shared/api/client";

export type RunStatus = {
  run_id: string;
  inquiry_id: string;
  attempt_no: number;
  run_status: "running" | "finished";
  status: string | null;
  inputs_done: number;
  inputs_total: number;
  eta_seconds: number;
  stop_reason: string | null;
  unreadable_reason: string | null;
};

/** ⑤ #8。2〜3秒間隔でポーリングする。 */
export function fetchRun(runId: string): Promise<RunStatus> {
  return request<RunStatus>(`/api/v1/runs/${runId}`);
}

export type RerunResult = { run_id: string; attempt_no: number };

/** ⑤ #7。打ち切りで終わった案件だけ、1回まで再実行できる。 */
export function rerunInquiry(inquiryId: string): Promise<RerunResult> {
  return postJson<RerunResult>(`/api/v1/inquiries/${inquiryId}/runs`);
}

/** ⑤ #16。原本のダウンロード先（ブラウザにそのまま開かせる）。 */
export function originalUrl(inquiryId: string, inputId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return `${base}/api/v1/inquiries/${inquiryId}/inputs/${inputId}/original`;
}
