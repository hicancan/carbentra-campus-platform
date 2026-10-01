import { lazy, Suspense, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  Lightbulb,
  PlugZap,
  Radio,
  Settings2,
  ShieldQuestion,
  ToggleRight,
  Zap,
} from 'lucide-react'
import type { ChannelSnapshot } from '../lib/classroom-types'
import type { Device } from '../lib/types'
import { useResource } from '../lib/hooks'
import { permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import { controlReason } from '../lib/control-eligibility'
import { formatDate, formatNumber } from '../lib/format'
import {
  Button,
  Card,
  DefinitionList,
  ErrorState,
  Loading,
  Modal,
  Notice,
  SourceBadge,
  StatusBadge,
} from './ui'
import { BooleanState, ClassroomState } from './ClassroomState'
import DeviceControlPanel from './DeviceControlPanel'
import ProductHero from './ProductHero'
import { isProductFamily } from '../lib/product'
const ProductReference = lazy(() => import('./ProductReference'))

const products = {
  PRESENCE: {
    label: 'CARBENTRA Sense',
    note: '存在感知 · 只读传感',
    icon: Radio,
    className: 'sense',
  },
  SWITCH: {
    label: 'CARBENTRA Switch',
    note: '独立照明通道 · 能力约束控制',
    icon: ToggleRight,
    className: 'switch',
  },
  PLUG: { label: 'CARBENTRA Plug', note: '插座输出 · 功率计量', icon: PlugZap, className: 'plug' },
  METER: { label: '电能计量设备', note: '按有效绑定读取计量', icon: Zap, className: 'meter' },
  SENSOR: { label: '环境传感设备', note: '仅展示声明能力', icon: Radio, className: 'sense' },
}
export function displayChannelName(channel: ChannelSnapshot) {
  const names: Record<ChannelSnapshot['kind'], string> = {
    presence: '存在感知',
    lighting: '照明回路',
    socket: '插座回路',
    power: '有功功率',
    temperature: '温度观测',
    illuminance: '环境光',
    co2: '二氧化碳',
  }
  return channel.name.endsWith(` · ${channel.kind}`)
    ? channel.name.slice(0, -channel.kind.length) +
        names[channel.kind] +
        (channel.kind === 'lighting' && /^relay\.[1-3]$/.test(channel.channel_key)
          ? ` · 第 ${channel.channel_key.split('.').pop()} 路`
          : '')
    : channel.name
}
export function channelMeasurement(channel: ChannelSnapshot): string {
  if (channel.quality !== 'good' || !channel.value) return '未知'
  if (channel.kind === 'presence')
    return channel.value.occupancy === 'occupied'
      ? '有人'
      : channel.value.occupancy === 'vacant'
        ? '无人'
        : '未知'
  const value = channel.kind === 'power' ? channel.value.active_power_w : channel.value.number
  return value == null
    ? '未知'
    : `${formatNumber(value)} ${channel.unit === 'degC' ? '°C' : channel.unit === 'raw_count' ? '原始计数' : channel.unit || ''}`
}
function ControlDevice({ id, channel }: { id: string; channel: ChannelSnapshot }) {
  const device = useResource<Device>(`/devices/${encodeURIComponent(id)}`, { interval: 5000 })
  return device.isLoading ? (
    <Loading />
  ) : device.error ? (
    <ErrorState error={device.error} />
  ) : device.data ? (
    <DeviceControlPanel device={device.data} channel={channel} />
  ) : (
    <Notice tone="warning">设备身份未载入，不能申请控制</Notice>
  )
}
export default function ClassroomDeviceCard({
  channels,
  historical,
}: {
  channels: ChannelSnapshot[]
  historical: boolean
}) {
  const auth = useAuth()
  const [control, setControl] = useState<string | null>(null)
  const [evidence, setEvidence] = useState(false)
  const [reference, setReference] = useState(false)
  const first = channels[0]
  if (!first) return null
  const product = products[first.product_family]
  const powerChannel = channels.find(
    (c) => c.kind === 'power' || c.capabilities.includes('power.active'),
  )
  const presence = channels.find((c) => c.kind === 'presence')
  const canOperate = permissions.operate(auth.session?.user.role) && !historical
  const canControl =
    canOperate && channels.some((c) => c.controllable && c.allowed_actions.length > 0)
  const selectedChannel = channels.find((channel) => channel.channel_id === control)
  const controls = channels.filter((c) => ['lighting', 'socket'].includes(c.kind))
  const sourceModes = [...new Set(channels.map((c) => c.source_mode))]
  return (
    <Card className="room-device-card">
      <div className="room-device-head">
        {isProductFamily(first.product_family) ? (
          <ProductHero
            family={first.product_family}
            fallback={<product.icon size={35} strokeWidth={1.3} />}
          />
        ) : (
          <div className={`room-device-icon ${product.className}`}>
            <product.icon size={25} strokeWidth={1.5} />
          </div>
        )}
        <StatusBadge value={first.online_status} />
      </div>
      <h3>{product.label}</h3>
      <p className="room-device-subtitle">
        {first.source_mode === 'SIMULATED' && first.product_family === 'SWITCH'
          ? '独立继电器通道 · 执行回报非灯亮证明'
          : product.note}
      </p>
      <p className="room-device-subtitle monospace">{first.device_id}</p>
      <div className="room-device-reading">
        {presence ? (
          <>
            <UsersIcon />
            <strong>{channelMeasurement(presence)}</strong>
            <small>有效存在观测</small>
          </>
        ) : powerChannel ? (
          <>
            <Zap size={19} />
            <strong>
              {powerChannel.quality === 'good'
                ? formatNumber(powerChannel.value?.active_power_w)
                : '—'}
            </strong>
            <small>W · 有功功率</small>
          </>
        ) : (
          <>
            <Lightbulb size={19} />
            <strong>{controls.length}</strong>
            <small>已登记输出通道</small>
          </>
        )}
      </div>
      <div className="room-channel-list">
        {channels.map((channel) => (
          <div className="room-channel-row" key={channel.channel_id}>
            <div>
              <strong>{displayChannelName(channel)}</strong>
              <small>
                {channel.channel_key} ·{' '}
                {channel.quality === 'good'
                  ? channel.observed_at
                    ? formatDate(channel.observed_at)
                    : `知识时刻 ${formatDate(channel.effective_at)}`
                  : `观测${channel.quality === 'stale' ? '过期' : '未确认'}`}
              </small>
            </div>
            {channel.manual_hold_until && (
              <small className="channel-hold-label">
                此通道后台接管至 {formatDate(channel.manual_hold_until)}
              </small>
            )}
            <div className="room-channel-evidence">
              {['lighting', 'socket'].includes(channel.kind) ? (
                <div className="channel-state-triplet">
                  <div>
                    <small>请求状态</small>
                    <BooleanState
                      value={channel.quality === 'good' ? channel.value?.desired_on : null}
                    />
                  </div>
                  <div>
                    <small>执行回报</small>
                    <BooleanState
                      value={
                        channel.quality === 'good' ? channel.value?.actuator_reported_on : null
                      }
                    />
                  </div>
                  <div>
                    <small>物理反馈</small>
                    <BooleanState
                      value={channel.quality === 'good' ? channel.value?.output_present : null}
                      unavailable={!channel.feedback_supported}
                    />
                  </div>
                </div>
              ) : channel.kind === 'presence' ? (
                <ClassroomState
                  value={channel.quality === 'good' ? channel.value?.occupancy : 'unknown'}
                />
              ) : (
                <span>{channelMeasurement(channel)}</span>
              )}
            </div>
            {['lighting', 'socket'].includes(channel.kind) && (
              <Button
                variant="ghost"
                className="channel-control-button"
                disabled={!canOperate || !channel.controllable || !channel.allowed_actions.length}
                onClick={() => setControl(channel.channel_id)}
                title={historical ? '历史快照不可控制' : controlReason(channel.block_reason)}
                aria-label={`操作 ${channel.name} ${channel.channel_key}`}
              >
                <Settings2 size={13} />
                操作 {channel.channel_key}
              </Button>
            )}
          </div>
        ))}
      </div>
      <p className="room-device-provenance">
        {historical ? '历史快照只读 · ' : ''}
        {first.product_family === 'PRESENCE'
          ? '计划与存在观测分离；不存在温控或调光能力的推定'
          : first.product_family === 'SWITCH'
            ? '开关执行回报不证明灯具点亮；设备合计功率不能复制成每路计量'
            : '请求不等于执行；输出反馈也不构成现场安全隔离证明'}
      </p>
      <div className="room-device-footer">
        <div className="inline-gap">
          {sourceModes.map((mode) => (
            <SourceBadge key={mode} value={mode} />
          ))}
        </div>
        <div className="inline-gap">
          {isProductFamily(first.product_family) && (
            <Button variant="ghost" onClick={() => setReference(true)}>
              工程参考
            </Button>
          )}
          <Button variant="ghost" onClick={() => setEvidence(true)}>
            证据
          </Button>
        </div>
      </div>
      {controls.length > 0 && !canControl && !historical && (
        <p className="room-device-provenance" style={{ marginTop: 12, marginBottom: 0 }}>
          控制条件：{[...new Set(controls.map((c) => controlReason(c.block_reason)))].join('；')}
        </p>
      )}
      {selectedChannel && (
        <Modal
          title={`${product.label} · ${selectedChannel.channel_key} 通道操作`}
          onClose={() => setControl(null)}
        >
          <Notice>控制按明确设备、通道及负载单独复核。此房间状态摘要不授予控制权限。</Notice>
          <ControlDevice id={first.device_id} channel={selectedChannel} />
        </Modal>
      )}
      {reference && isProductFamily(first.product_family) && (
        <Modal title={`${product.label} · 工程参考`} onClose={() => setReference(false)}>
          <Suspense fallback={<Loading label="正在读取产品工程资料…" />}>
            <ProductReference family={first.product_family} />
          </Suspense>
        </Modal>
      )}
      {evidence && (
        <Modal title={`${product.label} · 通道证据`} onClose={() => setEvidence(false)}>
          {channels.map((channel) => (
            <div key={channel.channel_id}>
              <h3 className="section-title">{channel.name}</h3>
              <DefinitionList
                items={[
                  ['通道身份', channel.channel_id],
                  ['声明能力', channel.capabilities.join(' · ')],
                  ['观测质量', <StatusBadge value={channel.quality} />],
                  ['数据来源', <SourceBadge value={channel.source_mode} />],
                  ['源版本', channel.source_version],
                  [
                    '验证依据',
                    channel.verification_kind === 'independent_feedback'
                      ? '独立输出反馈'
                      : channel.verification_kind === 'actuator_reported_only'
                        ? '只有执行器回报，不证明灯亮或负载供电'
                        : '只读观测，不适用执行验证',
                  ],
                  ['此通道人工接管截止', formatDate(channel.manual_hold_until)],
                  [
                    '接管范围',
                    channel.manual_hold_scope === 'backend_edge'
                      ? '后台 / 边缘调度；不覆盖设备本地按键保护'
                      : '无后台接管',
                  ],
                  ['设备观测时间', formatDate(channel.observed_at)],
                  ['平台知识生效时间', formatDate(channel.effective_at)],
                  [
                    '时间依据',
                    channel.time_basis === 'authenticated_relative_receipt'
                      ? '认证相对龄 + 接收知识边界；设备 UTC 未知'
                      : channel.time_basis === 'device_observed'
                        ? '设备观测时间'
                        : channel.time_basis === 'received_only'
                          ? '仅接收时间，不等于设备观测时间'
                          : '时间依据未知',
                  ],
                  [
                    '测量相对龄',
                    channel.measurement_age_ms == null
                      ? '未知 / 不适用'
                      : `${formatNumber(channel.measurement_age_ms)} ms`,
                  ],
                  ['接收时间', formatDate(channel.received_at)],
                  ['有效截止', formatDate(channel.valid_until)],
                  [
                    '观测 / 安装绑定',
                    `${channel.observation_id ?? '未知'} / ${channel.binding_id ?? '未知'}`,
                  ],
                  ['质量标记', channel.quality_flags.join(' · ') || '无附加标记'],
                  [
                    '控制限制',
                    channel.block_reason
                      ? controlReason(channel.block_reason)
                      : '仍需独立设备授权核验',
                  ],
                ]}
              />
            </div>
          ))}
          <Link className="text-link" to={`/devices?device=${encodeURIComponent(first.device_id)}`}>
            完整设备档案
            <ArrowUpRight size={13} />
          </Link>
        </Modal>
      )}
    </Card>
  )
}
function UsersIcon() {
  return <ShieldQuestion size={19} />
}
