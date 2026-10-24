import type { Profile, Tokens } from '../types/api'

type Session = {
  user: Profile | null
  status: 'checking' | 'authenticated' | 'anonymous'
  message: string
  generation: number
}

function readTokens(): Tokens | null {
  try {
    const access_token = sessionStorage.getItem('access_token') || ''
    const refresh_token = sessionStorage.getItem('refresh_token') || ''
    return access_token || refresh_token ? { access_token, refresh_token, token_type: 'bearer' } : null
  } catch {
    return null
  }
}

let tokens = readTokens()
let session: Session = {
  user: null,
  status: tokens ? 'checking' : 'anonymous',
  message: '',
  generation: 0,
}
const listeners = new Set<() => void>()

function publish(next: Session) {
  session = next
  listeners.forEach((listener) => listener())
}

export function subscribeSession(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export const getSession = () => session
export const getTokens = () => tokens

export function setTokens(value: Tokens, generation: number) {
  if (generation !== session.generation) return false
  tokens = value
  try {
    sessionStorage.setItem('access_token', value.access_token)
    sessionStorage.setItem('refresh_token', value.refresh_token)
    sessionStorage.removeItem('username')
  } catch {
    return true
  }
  return true
}

export function clearSession(message = '') {
  tokens = null
  try {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
    sessionStorage.removeItem('username')
  } catch {
    tokens = null
  }
  publish({ user: null, status: 'anonymous', message, generation: session.generation + 1 })
}

export function setUser(user: Profile, generation: number) {
  if (generation !== session.generation) return
  publish({ ...session, user, status: 'authenticated', message: '' })
}
