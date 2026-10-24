import type { Tokens } from '../types/api'
import { clearSession, getSession, getTokens, setTokens } from './session'

export class ApiError extends Error {
  status: number
  uncertain: boolean

  constructor(message: string, status = 0, uncertain = false) {
    super(message)
    this.status = status
    this.uncertain = uncertain
  }
}

type Options = {
  method?: 'GET' | 'POST'
  json?: unknown
  body?: FormData
  signal?: AbortSignal
  public?: boolean
}

const expired = 'Не удалось восстановить сессию. Войдите снова.'
const apiPath = /^\/(?:auth\/(?:login|register|refresh|me|users(?:\/[a-f0-9-]+)?)|resumes(?:\/[a-f0-9-]+)?|vacancies(?:\/[a-f0-9-]+)?)$/i
let refreshing: { generation: number; promise: Promise<void> } | null = null

function assertSession(generation: number) {
  if (generation !== getSession().generation) throw new ApiError('Сессия изменилась. Повторите действие после входа.', 401)
}

function statusError(status: number, path: string, post: boolean) {
  if (path === '/auth/login' && status === 401) return new ApiError('Неверное имя пользователя или пароль.', status)
  if (path === '/auth/register' && (status === 400 || status === 409)) return new ApiError('Это имя пользователя уже занято.', status)
  const messages: Record<number, string> = {
    400: 'Не удалось принять данные. Проверьте заполненные поля.',
    401: expired,
    403: 'Нет доступа к этому действию.',
    404: 'Не найдено. Ресурс отсутствует или недоступен вашему аккаунту.',
    413: 'Файл слишком большой. Выберите файл меньшего размера.',
    422: path === '/resumes' ? 'Нужен корректный, непустой PDF или DOCX. Защищённый PDF не поддерживается.' : 'Проверьте введённые данные.',
    429: 'Слишком много запросов. Попробуйте немного позже.',
  }
  return new ApiError(messages[status] || 'Сервис временно недоступен. Попробуйте позже.', status, post && status >= 500)
}

async function send(path: string, options: Options, token: string | undefined, generation: number): Promise<Response> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  if (options.signal?.aborted) controller.abort()
  const timeout = setTimeout(abort, 30000)
  try {
    const response = await fetch(path, {
      method: options.method || 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
      signal: controller.signal,
      credentials: 'omit',
      redirect: 'error',
    })
    const bytes = await response.arrayBuffer()
    assertSession(generation)
    return new Response(response.status === 204 ? null : bytes, { status: response.status, headers: response.headers })
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    if (options.signal?.aborted) throw new DOMException('Запрос отменён', 'AbortError')
    throw new ApiError('Нет связи с сервером или истекло время ожидания. Проверьте подключение.', 0, options.method === 'POST')
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abort)
  }
}

async function refresh(generation: number) {
  assertSession(generation)
  if (refreshing?.generation === generation) return refreshing.promise
  const refreshToken = getTokens()?.refresh_token
  const promise = (async () => {
    try {
      if (!refreshToken) throw new ApiError(expired, 401)
      const response = await send('/auth/refresh', { method: 'POST', json: { refresh_token: refreshToken } }, undefined, generation)
      if (!response.ok) throw new ApiError(expired, 401)
      const value = await response.json() as Tokens
      if (!value.access_token || !value.refresh_token || value.token_type?.toLowerCase() !== 'bearer') throw new ApiError(expired, 401)
      assertSession(generation)
      setTokens(value, generation)
    } catch {
      if (getSession().generation === generation) clearSession(expired)
      throw new ApiError(expired, 401)
    }
  })()
  refreshing = { generation, promise }
  try {
    await promise
  } finally {
    if (refreshing?.promise === promise) refreshing = null
  }
}

export async function request(path: string, options: Options = {}): Promise<Response> {
  if (!apiPath.test(path)) throw new ApiError('Недопустимый адрес запроса.')
  const generation = getSession().generation
  let refreshed = false
  let token = options.public ? undefined : getTokens()?.access_token
  if (!options.public && !token) {
    await refresh(generation)
    refreshed = true
    token = getTokens()?.access_token
  }
  let response = await send(path, options, token, generation)
  if (response.status === 401 && !options.public) {
    if (refreshed) {
      clearSession(expired)
      throw new ApiError(expired, 401)
    }
    if (token === getTokens()?.access_token) await refresh(generation)
    assertSession(generation)
    response = await send(path, options, getTokens()?.access_token, generation)
    if (response.status === 401) {
      clearSession(expired)
      throw new ApiError(expired, 401)
    }
  }
  if (!response.ok) throw statusError(response.status, path, options.method === 'POST')
  return response
}

export async function requestJson<T>(path: string, options: Options = {}): Promise<T> {
  const generation = getSession().generation
  const response = await request(path, options)
  try {
    const data = await response.json() as T
    assertSession(generation)
    return data
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    throw new ApiError('Сервер вернул некорректный ответ.', response.status, options.method === 'POST')
  }
}

export function errorMessage(cause: unknown) {
  return cause instanceof Error ? cause.message : 'Не удалось выполнить действие. Попробуйте ещё раз.'
}
