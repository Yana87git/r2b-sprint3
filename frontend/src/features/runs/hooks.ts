"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchRun,
  rerunInquiry,
  type RerunResult,
  type RunStatus,
} from "./api";

const POLL_MS = 3000;

export function useRun(runId: string) {
  return useQuery<RunStatus>({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId),
    // 終わったら止める（⑤ #8 の実行の型: POST 202 → GET でポーリング）
    refetchInterval: (query) =>
      query.state.data?.run_status === "finished" ? false : POLL_MS,
    // 画面を離れていても進める（タブが非アクティブでも止めない）
    refetchIntervalInBackground: true,
  });
}

export function useRerun(
  inquiryId: string,
  onStarted: (result: RerunResult) => void,
) {
  return useMutation({
    mutationFn: () => rerunInquiry(inquiryId),
    onSuccess: onStarted,
  });
}
