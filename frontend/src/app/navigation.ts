import { useSyncExternalStore } from 'react'

const subscribe = (listener: () => void) => {
  window.addEventListener('popstate', listener)
  return () => window.removeEventListener('popstate', listener)
}

export function navigate(path: string, replace = false) {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\')) return
  window.history[replace ? 'replaceState' : 'pushState'](null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export const useLocation = () => useSyncExternalStore(subscribe, () => window.location.pathname + window.location.search)
