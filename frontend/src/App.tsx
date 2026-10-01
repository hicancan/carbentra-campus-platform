import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './lib/auth'
import { ScopeProvider } from './lib/scope'
import Layout from './components/Layout'
import { EmptyState, ErrorState, Loading } from './components/ui'
import Login from './pages/Login'
const Overview = lazy(() => import('./pages/Overview'))
const Campus = lazy(() => import('./pages/Campus'))
const Classrooms = lazy(() => import('./pages/Classrooms'))
const Classroom = lazy(() => import('./pages/Classroom'))
const Energy = lazy(() => import('./pages/Energy'))
const Accounting = lazy(() => import('./pages/Accounting'))
const Devices = lazy(() => import('./pages/Devices'))
const Topology = lazy(() => import('./pages/Topology'))
const Alarms = lazy(() => import('./pages/Alarms'))
const Strategies = lazy(() => import('./pages/Strategies'))
const Commands = lazy(() => import('./pages/Commands'))
const Reports = lazy(() => import('./pages/Reports'))
const Schedules = lazy(() => import('./pages/Schedules'))
const System = lazy(() => import('./pages/System'))
const client = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, refetchOnWindowFocus: true, retry: 1 },
    mutations: { retry: false },
  },
})
function Application() {
  const auth = useAuth()
  if (auth.loading)
    return (
      <div className="boot-screen">
        <div className="boot-mark">C</div>
        <Loading label="正在建立安全会话…" />
      </div>
    )
  if (auth.error && !auth.session)
    return (
      <div className="boot-screen">
        <ErrorState error={auth.error} retry={auth.refresh} />
      </div>
    )
  if (!auth.session) return <Login />
  return (
    <ScopeProvider>
      <Suspense fallback={<Loading label="正在打开工作空间…" />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="campus" element={<Campus />} />
            <Route path="classrooms" element={<Classrooms />} />
            <Route path="classrooms/:spaceId" element={<Classroom />} />
            <Route path="energy" element={<Energy />} />
            <Route path="carbon" element={<Accounting />} />
            <Route path="devices" element={<Devices />} />
            <Route path="topology" element={<Topology />} />
            <Route path="alarms" element={<Alarms />} />
            <Route path="strategies" element={<Strategies />} />
            <Route path="commands" element={<Commands />} />
            <Route path="reports" element={<Reports />} />
            <Route path="schedules" element={<Schedules />} />
            <Route path="system" element={<System />} />
            <Route path="login" element={<Navigate to="/" replace />} />
            <Route
              path="*"
              element={
                <EmptyState
                  title="页面不存在"
                  description="通过左侧导航继续浏览工作空间"
                  action={
                    <Link className="button button-primary" to="/">
                      返回运行总览
                    </Link>
                  }
                />
              }
            />
          </Route>
        </Routes>
      </Suspense>
    </ScopeProvider>
  )
}
export default function App() {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <AuthProvider>
          <Application />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
