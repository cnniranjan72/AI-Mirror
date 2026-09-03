import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'

export function useApi(fn, deps = [], options = {}) {
  const { enabled = true, onError, pollMs = 0 } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  const execute = useCallback(async (opts = {}) => {
    if (!enabled) { setLoading(false); return }
    // Polling re-fetches use `silent` so an in-flight background refresh
    // doesn't flash the loading skeleton over data the user is looking at.
    if (!opts.silent) setLoading(true)
    setError(null)
    try {
      const result = await fn()
      if (mountedRef.current) setData(result)
    } catch (err) {
      if (mountedRef.current) {
        setError(err?.response?.data?.detail || err?.message || 'Request failed')
        if (onError) onError(err)
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, deps)

  useEffect(() => {
    mountedRef.current = true
    execute()
    return () => { mountedRef.current = false }
  }, [execute])

  // Optional background polling — off by default. Skips ticks while the tab
  // is hidden so a page left open in a background tab doesn't keep hammering
  // the backend, and catches back up on the next visible tick.
  useEffect(() => {
    if (!pollMs) return
    const id = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      execute({ silent: true })
    }, pollMs)
    return () => clearInterval(id)
  }, [pollMs, execute])

  return { data, loading, error, refetch: execute }
}

export function useIdentity(userId) {
  const { data: current, loading: currentLoading, error: currentError, refetch: refetchCurrent } = useApi(() => api.getCurrentIdentity(userId), [userId])
  const { data: summary } = useApi(() => api.getCognitiveSummary(userId), [userId])
  const { data: snapshots } = useApi(() => api.getIdentitySnapshot(userId, 20), [userId])
  return { current, summary, snapshots, loading: currentLoading, error: currentError, refetch: refetchCurrent }
}

export function useEvidence(userId) {
  return useApi(() => api.getEvidence(userId, '', 100), [userId])
}

export function useInferences(userId, options) {
  return useApi(() => api.getInferences(userId, 50), [userId], options)
}

export function useReflections(userId, options) {
  return useApi(() => api.getReflections(userId, 20), [userId], options)
}

export function useMemories(userId, options) {
  return useApi(() => api.getMemories(userId, 25), [userId], options)
}

export function useBehaviorObjects(userId, options) {
  return useApi(() => api.getBehaviorObjects(userId, 50), [userId], options)
}

export function useTraces(userId) {
  return useApi(() => api.getTraces(userId, 20), [userId])
}

export function useTraceDetail(traceId) {
  return useApi(() => api.getTraceDetail(traceId), [traceId], { enabled: !!traceId })
}

export function useCognitiveMetrics(userId, metricName = '') {
  const { data, loading, error, refetch } = useApi(() => api.getCognitiveMetrics(userId, metricName, 200), [userId, metricName])
  return { metrics: data, loading, error, refetch }
}

export function useProfile() {
  return useApi(() => api.getProfile(), [])
}

export function useSessions() {
  return useApi(() => api.getSessions(), [])
}

export function useChatHistory(userId, conversationId) {
  return useApi(() => api.getChatHistory(userId, conversationId), [userId, conversationId])
}

export function useV3Health() {
  return useApi(() => api.v3Health(), [])
}

export function useCharacterState(userId, pollMs = 0) {
  return useApi(() => api.getCharacterState(userId), [userId], { pollMs })
}
