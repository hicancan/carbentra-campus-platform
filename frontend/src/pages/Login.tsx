import { useState } from 'react'
import {
  ArrowRight,
  ArrowUpRight,
  Building2,
  Leaf,
  LockKeyhole,
  RadioTower,
  ShieldCheck,
} from 'lucide-react'
import { useAuth } from '../lib/auth'
import { Button, ErrorState, Field } from '../components/ui'
export default function Login() {
  const auth = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">
            <Leaf size={25} />
          </span>
          <div>
            <strong>碳迹未来</strong>
            <span>CARBENTRA CAMPUS</span>
          </div>
        </div>
        <div className="login-story-content">
          <span className="eyebrow">ENERGY, WITH CLARITY.</span>
          <h1>
            让校园的每一份能量
            <br />
            <em>都有迹可循。</em>
          </h1>
          <p>
            连接空间、设备与数据。
            <br />
            从可信计量到审慎控制，构建可持续的智慧校园。
          </p>
          <div className="campus-illustration" aria-hidden="true">
            <div className="iso-grid" />
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className={`iso-building iso-${i}`}>
                <div />
                <span />
                <i />
              </div>
            ))}
            <div className="illustration-tag">
              <RadioTower size={15} />云 · 边 · 端协同
            </div>
          </div>
          <div className="login-features">
            <span>
              <Building2 size={17} />
              全校园空间管理
            </span>
            <span>
              <ShieldCheck size={17} />
              可追溯的安全控制
            </span>
          </div>
        </div>
        <div className="login-story-footer">
          基于 AIoT 云边端协同的高校智慧能碳管理平台
          <ArrowUpRight size={17} />
        </div>
      </section>
      <section className="login-form-side">
        <div className="login-form">
          <div className="login-icon">
            <LockKeyhole size={24} />
          </div>
          <div className="eyebrow">WELCOME BACK</div>
          <h2>登录工作空间</h2>
          <p>使用您的平台账户，继续管理校园能碳运行</p>
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              setError(null)
              setLoading(true)
              try {
                await auth.login(username, password)
              } catch (e) {
                setError(e)
              } finally {
                setLoading(false)
              }
            }}
          >
            <Field label="账户">
              <input
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入账户名"
                required
                autoFocus
              />
            </Field>
            <Field label="密码">
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                required
              />
            </Field>
            {!!error && <ErrorState error={error} compact />}
            <Button type="submit" variant="primary" loading={loading}>
              进入平台
              <ArrowRight size={17} />
            </Button>
          </form>
          <p className="login-security">
            <ShieldCheck size={14} />
            会话保护 · 角色权限 · 操作留痕
          </p>
        </div>
        <div className="login-footer">
          <span>
            Powered by <strong>CARBENTRA</strong>
          </span>
          <span>智慧校园 · 低碳未来</span>
        </div>
      </section>
    </main>
  )
}
