import { createContext, useContext, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, isUnauthorized, setCsrfToken } from './api'
import type { Session } from './api'
interface AuthValue {
  session?: Session
  loading: boolean
  error: unknown
  refresh: () => void
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}
const AuthContext = createContext<AuthValue | null>(null)
export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient()
  const query = useQuery<Session | null>({
    queryKey: ['session'],
    queryFn: ({ signal }) => api.get<Session>('/auth/me', signal),
    retry: false,
    staleTime: 60_000,
    // Anonymous refreshes must never unmount an in-progress login form.
    refetchInterval: (query) => (query.state.data ? 60_000 : false),
    refetchOnWindowFocus: (query) => Boolean(query.state.data),
    refetchOnReconnect: (query) => Boolean(query.state.data),
  })
  useEffect(() => {
    setCsrfToken(query.data?.csrf_token || '')
  }, [query.data])
  useEffect(() => {
    if (isUnauthorized(query.error)) {
      setCsrfToken('')
      client.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' })
      client.setQueryData(['session'], null)
    }
  }, [client, query.error])
  useEffect(() => {
    const expired = () => {
      setCsrfToken('')
      client.setQueryData(['session'], null)
      client.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' })
      void client.invalidateQueries({ queryKey: ['session'] })
    }
    window.addEventListener('carbentra:session-expired', expired)
    return () => window.removeEventListener('carbentra:session-expired', expired)
  }, [client])
  return (
    <AuthContext.Provider
      value={{
        session: query.error && isUnauthorized(query.error) ? undefined : query.data || undefined,
        loading: query.isPending,
        error: isUnauthorized(query.error) ? null : query.error,
        refresh: () => {
          void query.refetch()
        },
        login: async (username, password) => {
          const result = await api.post<Session>('/auth/login', { username, password })
          // An older anonymous/session refresh must not overwrite the new identity.
          await client.cancelQueries({ queryKey: ['session'] })
          setCsrfToken(result.csrf_token)
          client.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' })
          client.setQueryData(['session'], result)
        },
        logout: async () => {
          await api.post('/auth/logout')
          await client.cancelQueries({ queryKey: ['session'] })
          setCsrfToken('')
          client.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' })
          client.setQueryData(['session'], null)
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider is required')
  return value
}
