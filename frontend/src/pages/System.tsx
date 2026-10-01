import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  Cpu,
  Database,
  HardDrive,
  LockKeyhole,
  RadioTower,
  Save,
  Server,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { api, permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import type { SystemStatus } from '../lib/types'
import UserManagement from '../components/UserManagement'
import { formatDate, formatNumber, roleLabel } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  ErrorState,
  Field,
  JsonView,
  Loading,
  Notice,
  PageHeader,
  RefreshButton,
  SourceBadge,
  StatusBadge,
} from '../components/ui'
interface Settings {
  stale_after_seconds: number
  offline_after_seconds: number
  [key: string]: unknown
}
function SettingsForm({ settings }: { settings: Settings }) {
  const client = useQueryClient()
  const [stale, setStale] = useState(settings.stale_after_seconds)
  const [offline, setOffline] = useState(settings.offline_after_seconds)
  const mutation = useMutation({
    mutationFn: () =>
      api.patch<Settings>('/settings', {
        stale_after_seconds: stale,
        offline_after_seconds: offline,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  return (
    <form
      className="form-stack"
      onSubmit={(e) => {
        e.preventDefault()
        mutation.mutate()
      }}
    >
      <div className="form-grid">
        <Field label="遥测过期阈值（秒）">
          <input
            type="number"
            min="10"
            max="3600"
            value={stale}
            onChange={(e) => setStale(Number(e.target.value))}
            required
          />
        </Field>
        <Field label="设备离线阈值（秒）">
          <input
            type="number"
            min={stale + 1}
            max="86400"
            value={offline}
            onChange={(e) => setOffline(Number(e.target.value))}
            required
          />
        </Field>
      </div>
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {mutation.isSuccess && <Notice tone="success">运行阈值已更新并记录审计</Notice>}
      <Button type="submit" variant="primary" loading={mutation.isPending}>
        <Save size={15} />
        保存运行阈值
      </Button>
    </form>
  )
}
export default function System() {
  const auth = useAuth()
  const status = useResource<SystemStatus>('/system/status', { interval: 10000 })
  const settings = useResource<Settings>('/settings')
  const d = status.data
  return (
    <>
      <PageHeader
        eyebrow="SYSTEM OPERATIONS"
        title="系统管理"
        description="查看服务健康、运行边界与角色权限，在明确的责任范围内管理平台。"
        actions={
          <RefreshButton
            onClick={() => {
              void status.refetch()
              void settings.refetch()
            }}
            fetching={status.isFetching}
          />
        }
      />
      {status.isLoading ? (
        <Loading />
      ) : status.error ? (
        <ErrorState
          error={status.error}
          retry={() => {
            void status.refetch()
          }}
        />
      ) : (
        d && (
          <>
            <div className="system-health-grid">
              {[
                {
                  title: '数据库',
                  value: d.database.status,
                  sub: d.database.dialect,
                  icon: Database,
                },
                {
                  title: '异步执行器',
                  value: d.worker.status,
                  sub: `最后心跳 ${formatDate(d.worker.last_tick_at)}`,
                  icon: Cpu,
                },
                {
                  title: '遥测接入',
                  value: d.ingestion.last_received_at ? 'online' : 'unknown',
                  sub: `${formatNumber(d.ingestion.total_samples, 0)} 条持久化样本`,
                  icon: RadioTower,
                },
                { title: '运行模式', value: d.mode, sub: `平台版本 ${d.version}`, icon: Server },
              ].map((s) => (
                <Card key={s.title} className="system-health-card">
                  <div>
                    <s.icon size={21} />
                    <StatusBadge value={s.value} />
                  </div>
                  <h3>{s.title}</h3>
                  <p>{s.sub}</p>
                </Card>
              ))}
            </div>
            <div className="two-col-grid">
              <Card>
                <CardHeader
                  title="执行安全边界"
                  subtitle="显式闭锁，拒绝模糊的控制成功"
                  actions={<LockKeyhole size={19} className="text-teal" />}
                />
                <div className="card-pad">
                  <div className="physical-lock">
                    <ShieldCheck size={37} />
                    <div>
                      <h3>
                        {d.physical_control.enabled
                          ? '部署开关已配置，设备仍需独立放行'
                          : '现场实际控制已关闭'}
                      </h3>
                      <p>{d.physical_control.reason}</p>
                    </div>
                    <Badge tone={d.physical_control.enabled ? 'amber' : 'teal'}>
                      {d.physical_control.enabled ? 'RELEASE GATED' : 'LOCKED'}
                    </Badge>
                  </div>
                  <DefinitionList
                    items={[
                      [
                        '现场执行通道',
                        d.physical_control.enabled
                          ? '部署开关已启用；每台设备仍需独立放行'
                          : '禁用',
                      ],
                      ['模拟执行器', d.simulation.enabled ? '已启用' : '未启用'],
                      ['模拟数据来源', <SourceBadge value={d.simulation.source_mode} />],
                      ['最近接收时间', formatDate(d.ingestion.last_received_at)],
                    ]}
                  />
                  <Notice>
                    投运检查、现场授权与物理释放均为独立前置条件。软件运行正常不等于设备完成强电资质或现场验收。
                  </Notice>
                </div>
              </Card>
              <Card>
                <CardHeader
                  title="账户与角色"
                  subtitle="服务端强制权限，页面操作同步限制"
                  actions={<Users size={19} className="text-muted" />}
                />
                <div className="card-pad">
                  <div className="profile-summary">
                    <span className="avatar large">
                      {auth.session?.user.display_name.slice(0, 1)}
                    </span>
                    <div>
                      <h3>{auth.session?.user.display_name}</h3>
                      <p>
                        {auth.session?.user.username} · {roleLabel(auth.session?.user.role)}
                      </p>
                    </div>
                  </div>
                  <DefinitionList
                    items={[
                      [
                        '运维设备 / 命令 / 告警',
                        permissions.operate(auth.session?.user.role) ? '允许' : '只读',
                      ],
                      [
                        '策略评估 / 报告生成',
                        permissions.analyze(auth.session?.user.role) ? '允许' : '只读',
                      ],
                      [
                        '策略审批 / 范围内账户',
                        permissions.administer(auth.session?.user.role) ? '允许' : '只读',
                      ],
                      [
                        '全局因子 / 电价 / 时效设置',
                        permissions.configureGlobal(auth.session?.user) ? '允许' : '只读',
                      ],
                      ['会话到期', formatDate(auth.session?.expires_at)],
                      ['会话保护', 'HttpOnly Cookie · CSRF · Origin 校验'],
                    ]}
                  />
                </div>
              </Card>
            </div>
            {d.warnings.length > 0 && (
              <Notice tone="warning" title="运行提示">
                {d.warnings.join('；')}
              </Notice>
            )}
            <div className="two-col-grid">
              <Card>
                <CardHeader
                  title="数据时效设置"
                  subtitle="过期与离线阈值决定数据质量和控制安全闭锁"
                  actions={<Activity size={19} className="text-muted" />}
                />
                <div className="card-pad">
                  {settings.isLoading ? (
                    <Loading compact />
                  ) : settings.error ? (
                    <ErrorState error={settings.error} />
                  ) : settings.data ? (
                    permissions.configureGlobal(auth.session?.user) ? (
                      <SettingsForm settings={settings.data} />
                    ) : (
                      <DefinitionList
                        items={[
                          ['过期阈值', `${settings.data.stale_after_seconds} 秒`],
                          ['离线阈值', `${settings.data.offline_after_seconds} 秒`],
                        ]}
                      />
                    )
                  ) : null}
                </div>
              </Card>
              <Card>
                <CardHeader
                  title="空间与产物状态"
                  subtitle="固定版本引用与可追溯空间来源"
                  actions={<HardDrive size={19} className="text-muted" />}
                />
                <div className="card-pad">
                  <JsonView value={d.spatial} />
                </div>
              </Card>
            </div>
            <UserManagement />
            <Card>
              <CardHeader
                title="关于碳迹未来"
                subtitle="Powered by CARBENTRA · 独立校园能碳管理项目"
              />
              <div className="card-pad about-project">
                <p>平台为独立实现，不代表大学官方发布或背书。空间参考与实时运行数据分别管理。</p>
                <p>
                  室外空间来源于{' '}
                  <a
                    href="https://www.openstreetmap.org/copyright"
                    target="_blank"
                    rel="noreferrer"
                  >
                    OpenStreetMap contributors
                  </a>{' '}
                  与{' '}
                  <a href="https://github.com/hicancan/njupt-map" target="_blank" rel="noreferrer">
                    hicancan / njupt-map
                  </a>
                  ；室内参考身份来源于{' '}
                  <a
                    href="https://github.com/hicancan/njupt-search"
                    target="_blank"
                    rel="noreferrer"
                  >
                    njupt-search
                  </a>
                  。各来源保留独立许可与版本记录。
                </p>
              </div>
            </Card>
          </>
        )
      )}
    </>
  )
}
