import type { components } from './generated-api'
export type User = components['schemas']['UserResponse']
export type Role = User['role']
export type SourceMode = components['schemas']['EnergySummaryResponse']['source_mode']
export type Session = components['schemas']['AuthResponse']
export interface Envelope<T> {
  data: T
  meta?: Record<string, unknown>
}
export class ApiError extends Error {
  status: number
  code: string
  requestId?: string
  fields: { location: string; message: string }[]
  constructor(
    message: string,
    status: number,
    code = 'REQUEST_FAILED',
    requestId?: string,
    details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.fields = Array.isArray(details)
      ? details
          .filter(
            (field) =>
              field &&
              Array.isArray(field.location) &&
              field.location.every(
                (value: unknown) => typeof value === 'string' || typeof value === 'number',
              ) &&
              typeof field.message === 'string',
          )
          .slice(0, 8)
          .map((field) => ({
            location: field.location.join('.').slice(0, 200),
            message: field.message.slice(0, 600),
          }))
      : []
  }
}
let csrfToken = ''
export const setCsrfToken = (token: string) => {
  csrfToken = token
}
export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
export function queryString(params: Record<string, string | number | boolean | undefined | null>) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params))
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  return query.size ? `?${query}` : ''
}
export async function request<T>(path: string, options: RequestInit = {}): Promise<Envelope<T>> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body) headers.set('Content-Type', 'application/json')
  if (options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase()) && csrfToken)
    headers.set('X-CSRF-Token', csrfToken)
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('无法连接服务。请检查网络或后端服务后重试。', 0, 'NETWORK_ERROR')
  }
  let body: Record<string, unknown> | null = null
  try {
    body = await response.json()
  } catch {
    /* A non-JSON proxy error is still surfaced. */
  }
  if (!response.ok) {
    const detail =
      body?.error && typeof body.error === 'object'
        ? (body.error as Record<string, unknown>)
        : body?.detail && typeof body.detail === 'object'
          ? (body.detail as Record<string, unknown>)
          : body
    const message =
      typeof detail?.message === 'string'
        ? detail.message
        : typeof body?.detail === 'string'
          ? body.detail
          : `请求未完成（HTTP ${response.status}）`
    if (response.status === 401 && path !== '/auth/me' && path !== '/auth/login')
      window.dispatchEvent(new Event('carbentra:session-expired'))
    throw new ApiError(
      message,
      response.status,
      String(detail?.code || 'REQUEST_FAILED'),
      typeof detail?.request_id === 'string'
        ? detail.request_id
        : response.headers.get('X-Request-ID') || undefined,
      detail?.details,
    )
  }
  if (!body || !('data' in body))
    throw new ApiError('服务返回的数据格式不符合约定', response.status, 'INVALID_RESPONSE')
  return body as unknown as Envelope<T>
}
export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }).then((r) => r.data),
  post: <T>(path: string, body?: unknown, idempotencyKey?: string) =>
    request<T>(path, {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
    }).then((r) => r.data),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }).then((r) => r.data),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }).then((r) => r.data),
}
export function isUnauthorized(error: unknown) {
  return error instanceof ApiError && error.status === 401
}
export const permissions = {
  operate: (role?: Role) => role === 'admin' || role === 'operator',
  analyze: (role?: Role) => ['admin', 'analyst'].includes(role || ''),
  administer: (role?: Role) => role === 'admin',
  configureGlobal: (user?: Pick<User, 'role' | 'campus_ids'>) =>
    user?.role === 'admin' && user.campus_ids === null,
}
