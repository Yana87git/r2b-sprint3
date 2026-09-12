"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchRun, type RunStatus } from "./api";

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
