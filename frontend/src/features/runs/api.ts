import { request } from "@/shared/api/client";

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
