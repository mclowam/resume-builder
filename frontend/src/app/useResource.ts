import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'

export function useResource<T>(load: (signal: AbortSignal) => Promise<T>, clearOnForbidden = false) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    load(controller.signal).then((result) => {
      if (!controller.signal.aborted) setData(result)
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) {
        if (clearOnForbidden && cause instanceof ApiError && cause.status === 403) setData(null)
        setError(cause)
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [load, revision, clearOnForbidden])

  return { data, error, loading, reload: () => setRevision((value) => value + 1) }
}
