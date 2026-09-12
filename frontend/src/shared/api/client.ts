// バックエンド（FastAPI）への薄い fetch ラッパ。
// orval は今回使わず（Slice 0-6 は対象外）、features/*/api.ts がこれを呼ぶ。
const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** ⑤ のエラー本体（detail に {code, message, ...}）。画面はコードで文面を出し分ける。 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    credentials: "include",
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = (body?.detail ?? {}) as Record<string, unknown>;
    throw new ApiError(
      response.status,
      typeof detail.code === "string" ? detail.code : "INTERNAL_ERROR",
      typeof detail.message === "string" ? detail.message : response.statusText,
      detail,
    );
  }
  return (await response.json()) as T;
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
