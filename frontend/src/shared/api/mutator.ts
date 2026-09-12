/**
 * Orval Custom Mutator (Fetch API版)
 *
 * orval v8が生成するAPIクライアントで使用するカスタムインスタンス。
 * Fetch APIベースで、共通のエラーハンドリング、トークン自動更新を提供する。
 *
 * 認証: httpOnly cookieベース（credentials: include）
 * - トークンはサーバーがcookieで管理
 * - XSS攻撃からトークンを保護
 * - 401時は自動的にリフレッシュエンドポイント呼び出し
 *
 * 注意: Client Component からのみ呼ばれる前提（window / cookie を使うため）。
 *
 * @see https://orval.dev/reference/configuration/output#mutator
 */

// Next.js: ブラウザに公開する環境変数は NEXT_PUBLIC_ プレフィックス（.env.local で設定）
const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

/**
 * トークンをリフレッシュする（cookieベース）
 */
async function refreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${baseURL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Cookie自動送信
    })

    if (response.ok) {
      return true // リフレッシュ成功
    } else {
      // リフレッシュ失敗 → ログインページへリダイレクト
      redirectToLogin()
      return false
    }
  } catch (error) {
    console.error('Token refresh failed:', error)
    redirectToLogin()
    return false
  } finally {
    isRefreshing = false
    refreshPromise = null
  }
}

/**
 * ログインページへリダイレクト
 */
function redirectToLogin(): void {
  window.location.href = '/login'
}

/**
 * カスタムインスタンス（orval用）
 *
 * Fetch APIで API呼び出しを実行し、以下の機能を提供：
 * - 自動的に Cookie を送信（credentials: include）
 * - 401 Unauthorized → トークン自動更新 → リクエスト再試行
 * - 認証失敗時 → ログインページへリダイレクト
 *
 * @template T - レスポンス型
 * @param url - リクエストURL
 * @param options - Fetch APIのRequestInit
 * @returns Promiseでラップされたレスポンス
 */
export const customInstance = async <T>(
  url: string,
  options?: RequestInit,
): Promise<T> => {
  const makeRequest = async (): Promise<Response> => {
    const headers = new Headers(options?.headers)

    // Content-Typeが未設定の場合のみデフォルトを設定
    if (
      !headers.has('Content-Type') &&
      options?.body &&
      typeof options.body === 'string'
    ) {
      headers.set('Content-Type', 'application/json')
    }

    return fetch(`${baseURL}${url}`, {
      ...options,
      headers,
      credentials: 'include', // Cookie自動送信（重要）
    })
  }

  let response = await makeRequest()

  // 401 Unauthorized処理（トークン自動更新）
  if (response.status === 401) {
    // リフレッシュ中でなければリフレッシュを試行
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = refreshToken()
    }

    // リフレッシュ完了を待機
    const refreshed = await refreshPromise

    if (refreshed) {
      // リフレッシュ成功：リクエストを再試行
      response = await makeRequest()
    } else {
      // リフレッシュ失敗：ログインページへリダイレクト
      redirectToLogin()
      throw new Error('Authentication failed')
    }
  }

  // まだ401の場合はリダイレクト
  if (response.status === 401) {
    redirectToLogin()
    throw new Error('Authentication failed')
  }

  // レスポンスをパース
  const data = await response.json()

  // レスポンスオブジェクトを構築
  return {
    data,
    status: response.status,
    headers: response.headers,
  } as T
}

/**
 * エラー型（orval用）
 *
 * API呼び出しで発生するエラーの型定義。
 * TanStack Queryのerror型として使用される。
 */
export type ErrorType<E> = E & { message?: string }

/**
 * Body型（orval用）
 *
 * リクエストボディの型定義。
 */
export type BodyType<B> = B
