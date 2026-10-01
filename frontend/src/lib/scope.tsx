import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { useResource } from './hooks'
import type { Campus } from './types'
const Context = createContext<{
  campusId: string
  setCampusId: (id: string) => void
  campuses: Campus[]
}>({ campusId: '', setCampusId: () => {}, campuses: [] })
export function ScopeProvider({ children }: { children: ReactNode }) {
  const [campusId, setCampusId] = useState('')
  const query = useResource<Campus[]>('/campuses?limit=500')
  return (
    <Context.Provider value={{ campusId, setCampusId, campuses: query.data || [] }}>
      {children}
    </Context.Provider>
  )
}
export const useScope = () => useContext(Context)
