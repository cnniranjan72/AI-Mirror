import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'

export function useApi(fn, deps = [], options = {}) {
  const { enabled = true, onError } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  const execute = useCallback(async () => {
    if (!enabled) { setLoading(false); return }
    setLoading(true)
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

  return { data, loading, error, refetch: execute }
}

export function useIdentity(userId) {
  const { data: current, loading: currentLoading } = useApi(() => api.getCurrentIdentity(userId), [userId])
  const { data: summary } = useApi(() => api.getCognitiveSummary(userId), [userId])
  const { data: snapshots } = useApi(() => api.getIdentitySnapshot(userId, 20), [userId])
  return { current, summary, snapshots, loading: currentLoading }
}

export function useEvidence(userId) {
  return useApi(() => api.getEvidence(userId, '', 100), [userId])
}

export function useInferences(userId) {
  return useApi(() => api.getInferences(userId, 50), [userId])
}

export function useReflections(userId) {
  return useApi(() => api.getReflections(userId, 20), [userId])
}

export function useBehaviorObjects(userId) {
  return useApi(() => api.getBehaviorObjects(userId, 50), [userId])
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

export function useChatHistory(userId) {
  return useApi(() => api.getChatHistory(userId), [userId])
}

export function useHealth() {
  return useApi(() => api.healthCheck(), [])
}

export function useV3Health() {
  return useApi(() => api.v3Health(), [])
}
