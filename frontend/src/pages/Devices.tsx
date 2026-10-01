import { IDENTIFIER_PATTERN } from '../lib/input-patterns'
import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Building2,
  Cpu,
  Download,
  Link2,
  Plus,
  RadioTower,
  Search,
  ShieldCheck,
  Thermometer,
  Zap,
} from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useDebounced, useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Device, DeviceDetail, Floor, Space, Telemetry, Topology } from '../lib/types'
import { downloadJson, formatDate, formatNumber, statusLabel } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  DefinitionList,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  JsonView,
  Loading,
  Modal,
  Notice,
  PageHeader,
  Pagination,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { BuildingFilter } from '../components/Filters'
import { LineChart } from '../components/charts'
import DeviceControlPanel from '../components/DeviceControlPanel'
import { deviceProductFamily } from '../lib/product'
const ProductReference = lazy(() => import('../components/ProductReference'))
function DeviceCreate({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const scope = useScope()
  const client = useQueryClient()
  const [id, setId] = useState('')
  const [name, setName] = useState('')
  const [campus, setCampus] = useState(scope.campusId || scope.campuses[0]?.id || '')
  const [kind, setKind] = useState('smart_plug')
  const [source, setSource] = useState('SIMULATED')
  const mutation = useMutation({
    mutationFn: () =>
      api.post<Device>('/devices', {
        id,
        name,
        campus_id: campus,
        kind,
        source_mode: source,
        critical: source !== 'SIMULATED',
        allow_control: false,
        capabilities:
          kind === 'smart_plug'
            ? ['metering', 'temperature', 'hold', 'shed', 'restore']
            : ['metering'],
      }),
    onSuccess: (result) => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onCreated(result.id)
      onClose()
    },
  })
  return (
    <Modal title="登记设备" onClose={onClose}>
      <Notice>
        新增设备默认未投运、未授权控制。真实或回放设备按关键负载保护登记，等待现场核验；登记不会触发执行。
      </Notice>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label="稳定设备 ID" hint="请使用不可随名称变化的唯一标识">
          <input
            required
            pattern={IDENTIFIER_PATTERN}
            value={id}
            onChange={(e) => setId(e.target.value)}
            maxLength={120}
            placeholder="例如 campus-plug-0001"
          />
        </Field>
        <Field label="显示名称">
          <input required value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        </Field>
        <Field label="所属校区">
          <select value={campus} onChange={(e) => setCampus(e.target.value)} required>
            <option value="">请选择校区</option>
            {scope.campuses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-grid">
          <Field label="设备类型">
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="smart_plug">智能插座</option>
              <option value="meter">电表</option>
              <option value="sensor">传感器</option>
            </select>
          </Field>
          <Field label="数据来源模式">
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="SIMULATED">SIMULATED</option>
              <option value="REPLAYED">REPLAYED</option>
              <option value="REAL">REAL</option>
            </select>
          </Field>
        </div>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button type="button" onClick={onClose}>
            取消
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            登记设备
          </Button>
        </div>
      </form>
    </Modal>
  )
}
function BindingForm({ device }: { device: Device }) {
  const client = useQueryClient()
  const scope = useScope()
  const [building, setBuilding] = useState(device.building_id || '')
  const [floor, setFloor] = useState(device.floor_id || '')
  const [space, setSpace] = useState(device.space_id || '')
  const [circuit, setCircuit] = useState(device.circuit_id || '')
  const [reason, setReason] = useState('')
  const [campus, setCampus] = useState(device.campus_id)
  const floors = useResource<Floor[]>(
    `/floors${queryString({ building_id: building, limit: 500 })}`,
    { enabled: !!building },
  )
  const spaces = useResource<Space[]>(
    `/spaces${queryString({ building_id: building, floor_id: floor, limit: 500 })}`,
    { enabled: !!building },
  )
  const topology = useResource<Topology>(
    `/topology${queryString({ campus_id: campus, building_id: building })}`,
    { enabled: !!campus },
  )
  const mutation = useMutation({
    mutationFn: () =>
      api.put<Device>(`/devices/${encodeURIComponent(device.id)}/binding`, {
        campus_id: campus,
        building_id: building || null,
        floor_id: floor || null,
        space_id: space || null,
        circuit_id: circuit || null,
        reason,
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
      <Notice tone="warning" title="变更绑定将关闭控制授权">
        移动设备后会清除投运与控制授权。请同时核验实际回路，不根据房间位置推断供电路径。
      </Notice>
      <Field label="校区">
        <select
          value={campus}
          onChange={(e) => {
            setCampus(e.target.value)
            setBuilding('')
            setFloor('')
            setSpace('')
            setCircuit('')
          }}
        >
          {scope.campuses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="楼栋">
        <BuildingFilter
          campusId={campus}
          value={building}
          onChange={(id) => {
            setBuilding(id)
            setFloor('')
            setSpace('')
            setCircuit('')
          }}
          allLabel="不绑定楼栋"
        />
      </Field>
      <Field label="楼层">
        <select
          value={floor}
          onChange={(e) => {
            setFloor(e.target.value)
            setSpace('')
          }}
          disabled={!building}
        >
          <option value="">不绑定楼层</option>
          {floors.data?.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="房间 / 空间">
        <select
          value={space}
          onChange={(e) => {
            setSpace(e.target.value)
            const selectedSpace = spaces.data?.find((s) => s.id === e.target.value)
            if (selectedSpace) setFloor(selectedSpace.floor_id)
            setCircuit('')
          }}
          disabled={!building}
        >
          <option value="">不绑定房间</option>
          {spaces.data?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="电气回路">
        <select value={circuit} onChange={(e) => setCircuit(e.target.value)}>
          <option value="">不绑定回路</option>
          {topology.data?.circuits
            .filter(
              (c) =>
                c.campus_id === campus &&
                (c.building_id || '') === building &&
                (!c.space_id || c.space_id === space) &&
                c.source_mode === device.source_mode,
            )
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
        </select>
      </Field>
      <Field label="变更原因">
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          required
          minLength={3}
          maxLength={500}
        />
      </Field>
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {mutation.isSuccess && <Notice tone="success">空间绑定已更新；控制授权已关闭</Notice>}
      <Button variant="primary" type="submit" loading={mutation.isPending}>
        <Link2 size={15} />
        确认变更绑定
      </Button>
    </form>
  )
}
function DeviceSettings({ device }: { device: Device }) {
  const client = useQueryClient()
  const [name, setName] = useState(device.name)
  const [commissioned, setCommissioned] = useState(device.commissioned)
  const [allowControl, setAllowControl] = useState(device.allow_control)
  const [critical, setCritical] = useState(device.critical)
  const [dispatch, setDispatch] = useState(device.dispatch_mode || 'IN_PROCESS')
  const mutation = useMutation({
    mutationFn: () =>
      api.patch<Device>(`/devices/${encodeURIComponent(device.id)}`, {
        name,
        ...(device.source_mode === 'SIMULATED'
          ? { commissioned, allow_control: allowControl, critical, dispatch_mode: dispatch }
          : {}),
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
      <Field label="设备显示名称">
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      {device.source_mode === 'SIMULATED' ? (
        <>
          <Notice>以下授权仅用于模拟设备。现场控制仍由独立物理闭锁阻止。</Notice>
          <Field label="模拟执行通道">
            <select
              value={dispatch}
              onChange={(e) => setDispatch(e.target.value as 'IN_PROCESS' | 'VIRTUAL' | 'DISABLED')}
            >
              <option value="IN_PROCESS">内置模拟执行器</option>
              <option value="VIRTUAL">MQTT 虚拟边缘</option>
              <option value="DISABLED">停用执行</option>
            </select>
          </Field>
          {dispatch === 'VIRTUAL' && (
            <Notice>
              虚拟边缘需要已配置的模拟适配器与双向回执；未连接时命令会超时，不能宣称执行成功。
            </Notice>
          )}
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={commissioned}
              onChange={(e) => setCommissioned(e.target.checked)}
            />
            完成模拟投运
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={allowControl}
              onChange={(e) => setAllowControl(e.target.checked)}
            />
            允许模拟控制
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={critical}
              onChange={(e) => setCritical(e.target.checked)}
            />
            标记为关键负载（阻止削减）
          </label>
        </>
      ) : (
        <Notice tone="warning">
          真实设备投运与现场控制授权需要独立验收，网页不能解除物理安全边界。
        </Notice>
      )}
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {mutation.isSuccess && <Notice tone="success">设备设置已保存</Notice>}
      <Button variant="primary" type="submit" loading={mutation.isPending}>
        保存设置
      </Button>
    </form>
  )
}
export function DeviceDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const auth = useAuth()
  const query = useResource<DeviceDetail>(`/devices/${encodeURIComponent(id)}`, { interval: 5000 })
  const telemetry = useResource<Telemetry[]>(
    `/devices/${encodeURIComponent(id)}/telemetry?limit=120`,
    { interval: 10000 },
  )
  const [tab, setTab] = useState('overview')
  const d = query.data
  const canOperate = permissions.operate(auth.session?.user.role)
  useEffect(() => setTab('overview'), [id])
  return (
    <Drawer title={d?.name || '设备详情'} subtitle={id} onClose={onClose} wide>
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
        d && (
          <>
            <div className="device-detail-top">
              <span className="device-object">
                <Cpu size={47} />
                <i />
                <i />
                <i />
              </span>
              <div>
                <div className="inline-gap">
                  <SourceBadge value={d.source_mode} />
                  <StatusBadge value={d.status} />
                </div>
                <h3>{statusLabel(d.kind)}</h3>
                <p>
                  {d.profile_id} · revision {d.profile_revision}
                </p>
              </div>
            </div>
            <Tabs
              active={tab}
              onChange={setTab}
              items={[
                { id: 'overview', label: '实时状态' },
                { id: 'telemetry', label: '遥测证据' },
                ...(deviceProductFamily(d) ? [{ id: 'product', label: '产品参考' }] : []),
                { id: 'control', label: '控制申请' },
                ...(canOperate
                  ? [
                      { id: 'binding', label: '空间绑定' },
                      { id: 'settings', label: '设备设置' },
                    ]
                  : []),
              ]}
            />
            {tab === 'overview' && (
              <>
                <div className="device-live-grid">
                  <div>
                    <Zap size={17} />
                    <span>有功功率</span>
                    <strong>
                      {formatNumber(d.latest?.active_power_w)}
                      <small>W</small>
                    </strong>
                  </div>
                  <div>
                    <ActivityIcon />
                    <span>电压</span>
                    <strong>
                      {formatNumber(d.latest?.voltage_v)}
                      <small>V</small>
                    </strong>
                  </div>
                  <div>
                    <Thermometer size={17} />
                    <span>板载温度</span>
                    <strong>
                      {formatNumber(d.latest?.board_temperature_c)}
                      <small>°C</small>
                    </strong>
                  </div>
                  <div>
                    <RadioTower size={17} />
                    <span>累计输入</span>
                    <strong>
                      {formatNumber(d.latest?.energy_import_wh)}
                      <small>Wh</small>
                    </strong>
                  </div>
                </div>
                <DefinitionList
                  items={[
                    ['最近观测', formatDate(d.latest?.observed_at)],
                    ['平台接收', formatDate(d.latest?.received_at)],
                    ['数据质量', <StatusBadge value={d.latest?.quality} />],
                    [
                      '请求状态',
                      d.latest?.desired_on == null ? '未知' : d.latest.desired_on ? '开启' : '关闭',
                    ],
                    [
                      '输出反馈',
                      d.latest?.output_present == null
                        ? '未知'
                        : d.latest.output_present
                          ? '检测到输出'
                          : '未检测到输出（非验电证明）',
                    ],
                    ['投运状态', d.commissioned ? '已投运' : '未投运'],
                    ['关键负载保护', d.critical ? '已开启' : '未标记'],
                    ['控制授权', d.allow_control ? '已授权，仍需校验安全条件' : '未授权'],
                    [
                      '空间绑定',
                      d.building_id ? (
                        <Link
                          className="text-link"
                          to={`/campus?building=${encodeURIComponent(d.building_id)}${d.floor_id ? `&floor=${encodeURIComponent(d.floor_id)}` : ''}${d.space_id ? `&space=${encodeURIComponent(d.space_id)}` : ''}`}
                        >
                          <Building2 size={14} />
                          查看空间
                          <ArrowRight size={13} />
                        </Link>
                      ) : (
                        '未绑定'
                      ),
                    ],
                    ['执行通道', d.dispatch_mode || '未配置'],
                    ['设备能力', d.capabilities.join(' · ')],
                  ]}
                />
                <Notice>
                  输出反馈与命令回执都不能证明物理隔离。无实时占用证据时，房间占用始终为未知。
                </Notice>
                <CardHeader title="近期功率" subtitle="只连接本设备的有效观测" />
                {telemetry.error ? (
                  <ErrorState error={telemetry.error} compact />
                ) : (
                  <LineChart
                    unit="W"
                    points={[...(telemetry.data || [])]
                      .sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at))
                      .map((t) => ({
                        timestamp: t.observed_at,
                        value: t.quality === 'invalid' ? null : t.active_power_w,
                      }))}
                    height={200}
                  />
                )}
              </>
            )}
            {tab === 'telemetry' && (
              <>
                <div className="inline-between section-space">
                  <p className="text-muted small">保留启动纪元、样本序号、质量与原始 Wh</p>
                  <Button
                    onClick={() => downloadJson(telemetry.data, `${d.id}-telemetry.json`)}
                    disabled={!telemetry.data}
                  >
                    <Download size={14} />
                    导出样本
                  </Button>
                </div>
                {telemetry.isLoading ? (
                  <Loading />
                ) : telemetry.error ? (
                  <ErrorState error={telemetry.error} />
                ) : (
                  <DataTable
                    rows={telemetry.data || []}
                    rowKey={(t) => String(t.id)}
                    columns={[
                      { key: 'time', title: '观测时间', render: (t) => formatDate(t.observed_at) },
                      { key: 'power', title: 'W', render: (t) => formatNumber(t.active_power_w) },
                      {
                        key: 'energy',
                        title: 'Wh',
                        render: (t) => formatNumber(t.energy_import_wh),
                      },
                      {
                        key: 'seq',
                        title: '序号',
                        render: (t) => <span title={t.boot_epoch}>{t.sample_seq}</span>,
                      },
                      {
                        key: 'quality',
                        title: '质量',
                        render: (t) => <StatusBadge value={t.quality} />,
                      },
                    ]}
                  />
                )}
                <details className="details-block">
                  <summary>来源与注册证据</summary>
                  <JsonView value={d.provenance} />
                </details>
              </>
            )}
            {tab === 'product' && (
              <Suspense fallback={<Loading label="正在打开产品资料…" />}>
                <ProductReference
                  key={deviceProductFamily(d) || 'unknown'}
                  family={deviceProductFamily(d)}
                />
              </Suspense>
            )}
            {tab === 'control' && <DeviceControlPanel device={d} />}
            {tab === 'binding' && canOperate && <BindingForm device={d} />}
            {tab === 'settings' && canOperate && <DeviceSettings device={d} />}
          </>
        )
      )}
    </Drawer>
  )
}
function ActivityIcon() {
  return <Zap size={17} />
}
export default function Devices() {
  const auth = useAuth()
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const selected = params.get('device') || ''
  const selectedSpace = params.get('space') || ''
  const building = params.get('building') || ''
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [offset, setOffset] = useState(0)
  const [create, setCreate] = useState(false)
  const limit = 25
  const query = useCollection<Device>(
    `/devices${queryString({ campus_id: scope.campusId, building_id: building, space_id: selectedSpace, q, status, source_mode: source, offset, limit })}`,
  )
  const close = useCallback(() => {
    const next = new URLSearchParams(params)
    next.delete('device')
    setParams(next)
  }, [params, setParams])
  const closeCreate = useCallback(() => setCreate(false), [])
  const select = (id: string) => {
    const next = new URLSearchParams(params)
    next.set('device', id)
    setParams(next)
  }
  useEffect(() => setOffset(0), [scope.campusId, building, q, status, source])
  return (
    <>
      <PageHeader
        eyebrow="DEVICES & EDGE"
        title="设备与边缘"
        description="统一登记、空间绑定与遥测追踪，让每个点位都有清晰的身份和边界。"
        actions={
          permissions.operate(auth.session?.user.role) && (
            <Button variant="primary" onClick={() => setCreate(true)}>
              <Plus size={16} />
              登记设备
            </Button>
          )
        }
      />
      <div className="registry-summary">
        <div>
          <Cpu size={20} />
          <span>
            设备注册表
            <strong>
              {query.data?.meta?.total != null ? String(query.data.meta.total) : '—'} 台
            </strong>
          </span>
        </div>
        <p>
          <ShieldCheck size={17} />
          注册、数据来源、投运与控制授权相互独立。真实控制保持关闭。
        </p>
      </div>
      <Card>
        <div className="filter-bar table-filters">
          <label className="search-field">
            <Search size={16} />
            <input
              aria-label="搜索设备"
              placeholder="搜索设备名称或 ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <BuildingFilter
            value={building}
            onChange={(id) => setParams(id ? { building: id } : {})}
          />
          <select aria-label="设备状态" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">所有状态</option>
            <option value="online">在线</option>
            <option value="stale">数据过期</option>
            <option value="offline">离线</option>
            <option value="unknown">未知</option>
          </select>
          <select aria-label="数据来源" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">全部来源</option>
            <option value="SIMULATED">SIMULATED</option>
            <option value="REAL">REAL</option>
            <option value="REPLAYED">REPLAYED</option>
          </select>
        </div>
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
          <>
            <DataTable
              rows={query.data?.data || []}
              rowKey={(d) => d.id}
              onRowClick={(d) => select(d.id)}
              selected={selected}
              columns={[
                {
                  key: 'name',
                  title: '设备',
                  render: (d) => (
                    <div className="table-device">
                      <span>
                        <Cpu size={17} />
                      </span>
                      <strong>
                        {d.name}
                        <small>{d.id}</small>
                      </strong>
                    </div>
                  ),
                },
                { key: 'kind', title: '类型', render: (d) => statusLabel(d.kind) },
                {
                  key: 'source',
                  title: '来源',
                  render: (d) => <SourceBadge value={d.source_mode} />,
                },
                { key: 'status', title: '状态', render: (d) => <StatusBadge value={d.status} /> },
                {
                  key: 'power',
                  title: '有功功率 / W',
                  render: (d) => (
                    <strong className="numeric">{formatNumber(d.latest?.active_power_w)}</strong>
                  ),
                },
                { key: 'seen', title: '最近观测', render: (d) => formatDate(d.last_seen_at) },
                {
                  key: 'control',
                  title: '控制边界',
                  render: (d) => (
                    <Badge tone={d.critical ? 'amber' : 'muted'}>
                      {d.critical
                        ? '关键负载'
                        : !d.commissioned
                          ? '未投运'
                          : d.allow_control
                            ? '已授权'
                            : '闭锁'}
                    </Badge>
                  ),
                },
              ]}
              empty={
                <EmptyState title="没有匹配的设备" description="调整筛选条件，或登记新的设备" />
              }
            />
            <Pagination
              limit={limit}
              offset={offset}
              total={Number(query.data?.meta?.total || 0)}
              setOffset={setOffset}
            />
          </>
        )}
      </Card>
      {selected && <DeviceDetail id={selected} onClose={close} />}
      {create && <DeviceCreate onClose={closeCreate} onCreated={select} />}
    </>
  )
}
