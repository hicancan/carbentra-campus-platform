import { USERNAME_PATTERN } from '../lib/input-patterns'
import { useCallback, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Plus, Save, UserRoundCog } from 'lucide-react'
import { api, permissions } from '../lib/api'
import type { Role } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import { roleLabel } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  Drawer,
  ErrorState,
  Field,
  Loading,
  Notice,
  Tabs,
} from './ui'
interface Account {
  id: string
  username: string
  display_name: string
  role: Role
  campus_ids: string[] | null
  enabled: boolean
  is_dev_fixture: boolean
}
function UserForm({ user, onClose }: { user?: Account; onClose: () => void }) {
  const auth = useAuth()
  const scope = useScope()
  const client = useQueryClient()
  const [tab, setTab] = useState('profile')
  const [username, setUsername] = useState(user?.username || '')
  const [name, setName] = useState(user?.display_name || '')
  const [role, setRole] = useState<Role>(user?.role || 'viewer')
  const [enabled, setEnabled] = useState(user?.enabled ?? true)
  const [global, setGlobal] = useState(user ? user.campus_ids === null : false)
  const [campusIds, setCampusIds] = useState(user?.campus_ids || [])
  const [password, setPassword] = useState('')
  const [passwordAgain, setPasswordAgain] = useState('')
  const mutation = useMutation({
    mutationFn: () =>
      user
        ? api.patch<Account>(`/users/${encodeURIComponent(user.id)}`, {
            display_name: name,
            role,
            enabled,
            campus_ids: global ? null : campusIds,
          })
        : api.post<Account>('/users', {
            username,
            display_name: name,
            role,
            campus_ids: global ? null : campusIds,
            password,
          }),
    onSuccess: () => {
      setPassword('')
      setPasswordAgain('')
      void client.invalidateQueries({ queryKey: ['resource'] })
      if (user?.id === auth.session?.user.id) auth.refresh()
      onClose()
    },
  })
  const reset = useMutation({
    mutationFn: () => api.post(`/users/${encodeURIComponent(user!.id)}/password`, { password }),
    onSuccess: () => {
      setPassword('')
      setPasswordAgain('')
      if (user?.id === auth.session?.user.id) auth.refresh()
    },
  })
  return (
    <Drawer title={user ? `管理账户 · ${user.display_name}` : '创建平台账户'} onClose={onClose}>
      {user && (
        <Tabs
          active={tab}
          onChange={setTab}
          items={[
            { id: 'profile', label: '角色与范围' },
            { id: 'password', label: '重置密码' },
          ]}
        />
      )}
      <Notice tone="warning">
        更改角色、校区范围、启用状态或密码后，该账户既有会话会失效，需要重新登录。
      </Notice>
      {tab === 'profile' ? (
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault()
            if (!user && password !== passwordAgain) return
            mutation.mutate()
          }}
        >
          <Field label="登录账户名">
            <input
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              pattern={USERNAME_PATTERN}
              minLength={3}
              maxLength={80}
              disabled={!!user}
              autoComplete="off"
            />
          </Field>
          <Field label="显示名称">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
            />
          </Field>
          <Field label="角色">
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {(['viewer', 'analyst', 'operator', 'admin'] as Role[]).map((r) => (
                <option value={r} key={r}>
                  {roleLabel(r)}
                </option>
              ))}
            </select>
          </Field>
          <div className="scope-picker">
            <strong>授权校区范围</strong>
            {permissions.configureGlobal(auth.session?.user) ? (
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={global}
                  onChange={(e) => setGlobal(e.target.checked)}
                />
                <span>全部校区（包括后续新增校区）</span>
              </label>
            ) : (
              <p className="small text-muted">仅可授予当前管理员有权限访问的校区</p>
            )}
            {!global &&
              scope.campuses.map((c) => (
                <label className="checkbox-field" key={c.id}>
                  <input
                    type="checkbox"
                    checked={campusIds.includes(c.id)}
                    onChange={(e) =>
                      setCampusIds((ids) =>
                        e.target.checked ? [...ids, c.id] : ids.filter((id) => id !== c.id),
                      )
                    }
                  />
                  <span>{c.name}</span>
                </label>
              ))}
            {!global && !campusIds.length && (
              <p className="small text-muted">尚未选择校区：账户可以登录，但无校园数据访问范围</p>
            )}
          </div>
          {user ? (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              <span>启用账户</span>
            </label>
          ) : (
            <>
              <Field label="初始密码（至少 16 字符）">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={16}
                  maxLength={256}
                  required
                  autoComplete="new-password"
                />
              </Field>
              <Field label="再次输入密码">
                <input
                  type="password"
                  value={passwordAgain}
                  onChange={(e) => setPasswordAgain(e.target.value)}
                  minLength={16}
                  maxLength={256}
                  required
                  autoComplete="new-password"
                />
              </Field>
              {passwordAgain && passwordAgain !== password && (
                <p className="validation-error">两次密码不一致</p>
              )}
            </>
          )}
          {mutation.error && <ErrorState error={mutation.error} compact />}
          <Button
            variant="primary"
            type="submit"
            disabled={!user && password !== passwordAgain}
            loading={mutation.isPending}
          >
            <Save size={15} />
            {user ? '保存账户与授权' : '创建账户'}
          </Button>
        </form>
      ) : (
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault()
            if (password === passwordAgain) reset.mutate()
          }}
        >
          <Field label="新密码（至少 16 字符）">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={16}
              maxLength={256}
              required
              autoComplete="new-password"
            />
          </Field>
          <Field label="再次输入新密码">
            <input
              type="password"
              value={passwordAgain}
              onChange={(e) => setPasswordAgain(e.target.value)}
              minLength={16}
              maxLength={256}
              required
              autoComplete="new-password"
            />
          </Field>
          {passwordAgain && passwordAgain !== password && (
            <p className="validation-error">两次密码不一致</p>
          )}
          {reset.error && <ErrorState error={reset.error} compact />}
          {reset.isSuccess && <Notice tone="success">密码已更新，旧会话已撤销</Notice>}
          <Button
            variant="primary"
            type="submit"
            disabled={password !== passwordAgain || !password}
            loading={reset.isPending}
          >
            <KeyRound size={15} />
            重置密码并撤销旧会话
          </Button>
        </form>
      )}
    </Drawer>
  )
}
export default function UserManagement() {
  const auth = useAuth()
  const scope = useScope()
  const allowed = permissions.administer(auth.session?.user.role)
  const query = useResource<Account[]>('/users?limit=500', { enabled: allowed })
  const [selected, setSelected] = useState<Account | undefined>()
  const [open, setOpen] = useState(false)
  const close = useCallback(() => {
    setOpen(false)
    setSelected(undefined)
  }, [])
  if (!allowed) return null
  return (
    <>
      <Card>
        <CardHeader
          title="账户与范围管理"
          subtitle="按最小权限分配角色和校区；变更后立即撤销旧会话"
          actions={
            <Button
              onClick={() => {
                setSelected(undefined)
                setOpen(true)
              }}
            >
              <Plus size={15} />
              创建账户
            </Button>
          }
        />
        {query.isLoading ? (
          <Loading />
        ) : query.error ? (
          <ErrorState
            error={query.error}
            retry={() => {
              void query.refetch()
            }}
          />
        ) : (
          <DataTable
            rows={query.data || []}
            rowKey={(u) => u.id}
            onRowClick={(u) => {
              setSelected(u)
              setOpen(true)
            }}
            columns={[
              {
                key: 'name',
                title: '账户',
                render: (u) => (
                  <div className="table-device">
                    <span>
                      <UserRoundCog size={17} />
                    </span>
                    <strong>
                      {u.display_name}
                      <small>{u.username}</small>
                    </strong>
                  </div>
                ),
              },
              { key: 'role', title: '角色', render: (u) => roleLabel(u.role) },
              {
                key: 'scope',
                title: '校区范围',
                render: (u) =>
                  u.campus_ids === null
                    ? '全部校区'
                    : !u.campus_ids.length
                      ? '无校园数据访问'
                      : u.campus_ids
                          .map((id) => scope.campuses.find((c) => c.id === id)?.name || id)
                          .join('、'),
              },
              {
                key: 'enabled',
                title: '状态',
                render: (u) => (
                  <Badge tone={u.enabled ? 'teal' : 'muted'}>
                    {u.enabled ? '已启用' : '已停用'}
                  </Badge>
                ),
              },
              {
                key: 'fixture',
                title: '账户类型',
                render: (u) => (
                  <Badge tone={u.is_dev_fixture ? 'blue' : 'muted'}>
                    {u.is_dev_fixture ? '开发测试账户' : '平台账户'}
                  </Badge>
                ),
              },
            ]}
          />
        )}
      </Card>
      {open && <UserForm user={selected} onClose={close} />}
    </>
  )
}
