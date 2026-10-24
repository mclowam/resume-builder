import { useSyncExternalStore } from 'react'
import { getSession, subscribeSession } from '../api/session'

export const useSession = () => useSyncExternalStore(subscribeSession, getSession)
