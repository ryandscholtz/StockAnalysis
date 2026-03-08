import { useState, useEffect, Dispatch, SetStateAction } from 'react'

/**
 * Like useState, but persists to sessionStorage so state survives
 * client-side navigation within the same browser session.
 */
export function useSessionState<T>(
  key: string,
  defaultValue: T
): [T, Dispatch<SetStateAction<T>>] {
  const [state, setState] = useState<T>(() => {
    if (typeof window === 'undefined') return defaultValue
    try {
      const stored = sessionStorage.getItem(key)
      if (stored !== null) return JSON.parse(stored) as T
    } catch {}
    return defaultValue
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(state))
    } catch {}
  }, [key, state])

  return [state, setState]
}
