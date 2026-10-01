import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  Pencil,
  Plus,
  ChevronDown,
  ChevronRight,
  CircuitBoard,
  GitBranch,
  Network,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import CircuitEditor from '../components/CircuitEditor'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Circuit, Device, Topology as TopologyData } from '../lib/types'
import { formatNumber } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  EmptyState,
  ErrorState,
  Loading,
  Notice,
  PageHeader,
  SourceBadge,
  StatusBadge,
} from '../components/ui'
import { BuildingFilter } from '../components/Filters'
function CircuitTree({
  circuit,
  circuits,
  selected,
  onSelect,
  depth = 0,
  seen = new Set<string>(),
}: {
  circuit: Circuit
  circuits: Circuit[]
  selected: string
  onSelect: (id: string) => void
  depth?: number
  seen?: Set<string>
}) {
  const [open, setOpen] = useState(depth < 1)
  if (seen.has(circuit.id) || depth > 12)
    return <Notice tone="warning">检测到回路层级异常，请核验拓扑</Notice>
  const children = circuits.filter((c) => c.parent_id === circuit.id)
  const nextSeen = new Set(seen).add(circuit.id)
  return (
    <div className="circuit-tree-node">
      <div className={`circuit-tree-row ${selected === circuit.id ? 'selected' : ''}`}>
        <button
          className="tree-toggle"
          aria-label={`${open ? '收起' : '展开'} ${circuit.name}`}
          onClick={() => setOpen((v) => !v)}
          disabled={!children.length}
        >
          {children.length ? (
            open ? (
              <ChevronDown size={15} />
            ) : (
              <ChevronRight size={15} />
            )
          ) : (
            <span />
          )}
        </button>
        <button className="tree-select" onClick={() => onSelect(circuit.id)}>
          <span className="circuit-icon">
            {depth === 0 ? <Network size={19} /> : <CircuitBoard size={17} />}
          </span>
          <div>
            <strong>{circuit.name}</strong>
            <small>
              {circuit.kind} · {children.length} 个下级回路
            </small>
          </div>
          <SourceBadge value={circuit.source_mode} />
        </button>
      </div>
      {open && children.length > 0 && (
        <div className="circuit-tree-children">
          {children.map((c) => (
            <CircuitTree
              key={c.id}
              circuit={c}
              circuits={circuits}
              selected={selected}
              onSelect={onSelect}
              depth={depth + 1}
              seen={nextSeen}
            />
          ))}
        </div>
      )}
    </div>
  )
}
export default function Topology() {
  const auth = useAuth()
  const [editing, setEditing] = useState<Circuit | undefined>()
  const [editor, setEditor] = useState(false)
  const closeEditor = useCallback(() => {
    setEditor(false)
    setEditing(undefined)
  }, [])
  const scope = useScope()
  const [building, setBuilding] = useState('')
  const [selected, setSelected] = useState('')
  const query = useResource<TopologyData>(
    `/topology${queryString({ campus_id: scope.campusId, building_id: building })}`,
  )
  const d = query.data
  const roots = useMemo(() => {
    const ids = new Set(d?.circuits.map((c) => c.id))
    return d?.circuits.filter((c) => !c.parent_id || !ids.has(c.parent_id)) || []
  }, [d])
  const circuit = d?.circuits.find((c) => c.id === selected)
  const devices = d?.devices.filter((device) => device.circuit_id === selected) || []
  const meter = d?.devices.find((device) => device.id === circuit?.meter_device_id)
  return (
    <>
      <PageHeader
        eyebrow="ELECTRICAL TOPOLOGY"
        title="配电拓扑"
        description="独立于空间层级的供电关系，让计量边界、设备保护与控制路径清晰可见。"
        actions={
          <>
            <BuildingFilter
              value={building}
              onChange={(id) => {
                setBuilding(id)
                setSelected('')
              }}
            />
            {permissions.operate(auth.session?.user.role) && (
              <Button
                variant="primary"
                onClick={() => {
                  setEditing(undefined)
                  setEditor(true)
                }}
              >
                <Plus size={15} />
                创建回路
              </Button>
            )}
          </>
        }
      />
      <Notice title="空间位置与配电关系各自独立">
        设备在同一房间不代表共用回路。能源聚合按照计量层级去重，不将父表与子表重复相加。
      </Notice>
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
        <div className="topology-grid">
          <Card>
            <CardHeader
              title="电气层级"
              subtitle="校园总进线 → 楼栋回路 → 负载设备"
              actions={<Badge>{d?.circuits.length || 0} 个回路</Badge>}
            />
            <div className="topology-tree">
              {roots.map((c) => (
                <CircuitTree
                  key={c.id}
                  circuit={c}
                  circuits={d?.circuits || []}
                  selected={selected}
                  onSelect={setSelected}
                />
              ))}
              {!roots.length && (
                <EmptyState
                  title="暂无回路拓扑"
                  description="空间数据不能推断实际供电路径"
                  icon={<GitBranch size={30} />}
                />
              )}
            </div>
          </Card>
          <Card className="circuit-detail">
            {circuit ? (
              <>
                <CardHeader
                  title={circuit.name}
                  subtitle={circuit.id}
                  actions={
                    <>
                      <SourceBadge value={circuit.source_mode} />
                      {permissions.operate(auth.session?.user.role) && (
                        <Button
                          onClick={() => {
                            setEditing(circuit)
                            setEditor(true)
                          }}
                        >
                          <Pencil size={14} />
                          编辑
                        </Button>
                      )}
                    </>
                  }
                />
                <div className="card-pad">
                  <div className="circuit-metric">
                    <Zap size={24} />
                    <div>
                      <span>关联主计量当前功率</span>
                      <strong>
                        {formatNumber(meter?.latest?.active_power_w)}
                        <small>W</small>
                      </strong>
                    </div>
                  </div>
                  <DefinitionList
                    items={[
                      ['回路类型', circuit.kind],
                      [
                        '父级回路',
                        d?.circuits.find((c) => c.id === circuit.parent_id)?.name ||
                          '根节点 / 未绑定',
                      ],
                      ['主计量设备', circuit.meter_device_id || '未绑定'],
                      ['直接关联设备', devices.length],
                      ['计量质量', <StatusBadge value={meter?.latest?.quality} />],
                    ]}
                  />
                  <h3 className="section-title">直接关联设备</h3>
                  {devices.length ? (
                    <div className="topology-devices">
                      {devices.map((device) => (
                        <DeviceRow key={device.id} device={device} />
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="暂无直接关联设备"
                      description="子回路设备需展开对应回路查看"
                    />
                  )}
                  <Notice>
                    <ShieldCheck size={14} />
                    本拓扑为平台记录，不代替现场电气图纸和验电程序
                  </Notice>
                </div>
              </>
            ) : (
              <EmptyState
                title="选择一个回路"
                description="查看计量节点、层级关系与直接关联设备"
                icon={<Network size={36} />}
              />
            )}
          </Card>
        </div>
      )}
      {editor && <CircuitEditor circuit={editing} onClose={closeEditor} />}
    </>
  )
}
function DeviceRow({ device }: { device: Device }) {
  return (
    <Link to={`/devices?device=${encodeURIComponent(device.id)}`}>
      <span>
        <Zap size={16} />
      </span>
      <div>
        <strong>{device.name}</strong>
        <small>
          {formatNumber(device.latest?.active_power_w)} W ·{' '}
          {device.critical ? '关键负载' : '常规设备'}
        </small>
      </div>
      <StatusBadge value={device.status} />
      <ArrowUpRight size={14} />
    </Link>
  )
}
