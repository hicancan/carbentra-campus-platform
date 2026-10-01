import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { eventResourcePrefixes } from './live-events'
import { api, API_BASE, request } from './api'
export function useResource<T>(
  path: string,
  options?: {
    enabled?: boolean
    interval?: number | false | ((data: T | undefined) => number | false)
  },
) {
  return useQuery({
    queryKey: ['resource', path],
    queryFn: ({ signal }) => api.get<T>(path, signal),
    enabled: options?.enabled,
    refetchInterval:
      typeof options?.interval === 'function'
        ? (query) => (options.interval as (data: T | undefined) => number | false)(query.state.data)
        : (options?.interval ?? 30_000),
    retry: 1,
  })
}
export function useLiveEvents() {
  const [status, setStatus] = useState<'connecting' | 'live' | 'polling'>('connecting')
  const client = useQueryClient()
  useEffect(() => {
    const events = new EventSource(`${API_BASE}/events`, { withCredentials: true })
    const lastRefresh = new Map<string, number>()
    const refresh = (event: MessageEvent) => {
      setStatus('live')
      let type = ''
      try {
        type = String(JSON.parse(event.data).type || '')
      } catch {
        return
      }
      const domain = type.split('.')[0]
      const interval = domain === 'telemetry' ? 10_000 : 1500
      if (Date.now() - (lastRefresh.get(domain) || 0) < interval) return
      lastRefresh.set(domain, Date.now())
      const prefixes = eventResourcePrefixes(type)
      if (prefixes.length)
        void client.invalidateQueries(
          {
            predicate: (query) =>
              query.queryKey[0] === 'resource' &&
              typeof query.queryKey[1] === 'string' &&
              prefixes.some((prefix) => String(query.queryKey[1]).startsWith(prefix)),
          },
          { cancelRefetch: false },
        )
    }
    events.onopen = () => setStatus('live')
    events.onmessage = refresh
    events.onerror = () => setStatus('polling')
    for (const event of [
      'change',
      'state',
      'update',
      'telemetry',
      'telemetry.updated',
      'command',
      'command.updated',
      'alarm',
      'alarm.updated',
    ])
      events.addEventListener(event, refresh as EventListener)
    return () => events.close()
  }, [client])
  return status
}
export function useDebounced<T>(value: T, delay = 200) {
  const [result, setResult] = useState(value)
  useEffect(() => {
    const timeout = setTimeout(() => setResult(value), delay)
    return () => clearTimeout(timeout)
  }, [value, delay])
  return result
}

export function useCollection<T>(
  path: string,
  options?: { enabled?: boolean; interval?: number | false },
) {
  return useQuery({
    queryKey: ['resource', path, 'collection'],
    queryFn: ({ signal }) => request<T[]>(path, { signal }),
    enabled: options?.enabled,
    refetchInterval: options?.interval ?? 30_000,
    retry: 1,
  })
}
