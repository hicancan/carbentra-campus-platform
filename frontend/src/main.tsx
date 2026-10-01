import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
import './classrooms.css'
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) {
    return { error }
  }
  render() {
    return this.state.error ? (
      <main className="boot-screen">
        <div className="error-state">
          <h1>页面遇到异常</h1>
          <p>请重新加载页面。尚未提交的操作不会自动执行。</p>
          <button className="button button-primary" onClick={() => window.location.reload()}>
            重新加载
          </button>
          <details>
            <summary>错误详情</summary>
            <p>{this.state.error.message}</p>
          </details>
        </div>
      </main>
    ) : (
      this.props.children
    )
  }
}
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
