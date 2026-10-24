import type { Credentials, Profile, Tokens, User } from '../types/api'
import { ApiError, errorMessage, requestJson } from './client'
import { clearSession, getSession, getTokens, setTokens, setUser } from './session'

let restoring: Promise<void> | null = null

export function restoreSession() {
  if (restoring) return restoring
  if (getSession().status !== 'checking') return Promise.resolve()
  const generation = getSession().generation
  restoring = (async () => {
    try {
      const user = await getProfile()
      setUser(user, generation)
    } catch (cause) {
      if (generation === getSession().generation) clearSession(`${errorMessage(cause)} Войдите в аккаунт заново.`)
    }
  })().finally(() => { restoring = null })
  return restoring
}

export async function login(credentials: Credentials) {
  clearSession()
  const generation = getSession().generation
  try {
    const tokens = await requestJson<Tokens>('/auth/login', { method: 'POST', json: credentials, public: true })
    if (!tokens.access_token || !tokens.refresh_token || tokens.token_type?.toLowerCase() !== 'bearer') throw new ApiError('Сервер вернул некорректный ответ.')
    if (!setTokens(tokens, generation)) throw new ApiError('Вход отменён.')
    const user = await getProfile()
    if (generation !== getSession().generation || !getTokens()) throw new ApiError('Вход отменён.')
    setUser(user, generation)
  } catch (cause) {
    if (generation === getSession().generation) clearSession()
    throw cause
  }
}

export const logout = () => clearSession()
export const register = (credentials: Credentials) => requestJson<{ user_id: string; username: string }>('/auth/register', { method: 'POST', json: credentials, public: true })
export const getProfile = (signal?: AbortSignal) => requestJson<Profile>('/auth/me', { signal })
export const getUsers = (signal?: AbortSignal) => requestJson<User[]>('/auth/users', { signal })
export const getUser = (id: string, signal?: AbortSignal) => requestJson<User>(`/auth/users/${id}`, { signal })
