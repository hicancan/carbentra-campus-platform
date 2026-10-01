export const formatNumber = (value: number | null | undefined, digits = 1) =>
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value)
    : '—'
export const formatDate = (value?: string | null, options?: Intl.DateTimeFormatOptions) =>
  value && !Number.isNaN(new Date(value).getTime())
    ? new Intl.DateTimeFormat(
        'zh-CN',
        options || {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        },
      ).format(new Date(value))
    : '未知'
export const formatTime = (value?: string | null) =>
  formatDate(value, { hour: '2-digit', minute: '2-digit', hour12: false })
export const shortId = (value?: string, length = 14) =>
  value ? (value.length > length ? `${value.slice(0, length)}…` : value) : '—'
export const roleLabel = (role?: string) =>
  ({ admin: '平台管理员', operator: '运维操作员', analyst: '能碳分析员', viewer: '只读访客' })[
    role || ''
  ] || '未知角色'
export const statusLabel = (status?: string | null): string =>
  ({
    SIMULATED: '模拟数据',
    REAL: '真实接入',
    REPLAYED: '历史回放',
    UNKNOWN: '来源未知',
    MIXED: '混合来源',
    fresh: '新鲜',
    stale: '已过期',
    offline: '离线',
    connected: '已连接',
    running: '运行中',
    not_started: '未启动',
    online: '在线',
    unknown: '未知',
    invalid: '无效',
    valid: '有效',
    good: '正常',
    partial: '覆盖不完整',
    complete: '完整',
    active: '待处理',
    open: '待处理',
    acknowledged: '已确认',
    acknowledged_unverified: '设备已应答 · 未物理验证',
    resolved: '已解决',
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    warning: '警告',
    info: '提示',
    requested: '待下发',
    queued: '排队中',
    dispatched: '已下发',
    verified: '已验证',
    rejected: '已拒绝',
    failed: '执行失败',
    timed_out: '已超时',
    expired: '已过期',
    pending: '待处理',
    draft: '草稿',
    evaluated: '已评估',
    approved: '已批准',
    shadow: '影子运行',
    enabled: '已启用',
    disabled: '已禁用',
    healthy: '健康',
    degraded: '降级',
    occupied: '有人',
    vacant: '无人',
    unoccupied: '无人',
    model_estimate: '模型估计',
    baseline_estimate: '基线估计',
    partial_estimate: '部分范围估计',
    insufficient_data: '数据不足',
    unavailable: '不可用',
    estimated: '估算',
    scheduled: '已安排',
    cancelled: '已取消',
    REFERENCE: '参考计划',
    teaching: '教学',
    holiday: '节假日',
    event: '活动',
    maintenance: '检修',
    uncommissioned: '未投运',
    commissioned: '已投运',
    simulated: '模拟',
    real: '真实',
    meter: '电表',
    smart_plug: '智能插座',
    switch: '三路智能开关',
    light: '照明执行器',
    presence: '存在感知终端',
    sensor: '传感器',
    gateway: '边缘网关',
    on: '开启',
    off: '关闭',
  })[status || ''] ||
  status ||
  '未知'
export function statusTone(status?: string | null): 'teal' | 'amber' | 'red' | 'blue' | 'muted' {
  if (
    [
      'REAL',
      'fresh',
      'online',
      'good',
      'valid',
      'complete',
      'resolved',
      'verified',
      'approved',
      'healthy',
      'connected',
      'running',
      'commissioned',
    ].includes(status || '')
  )
    return 'teal'
  if (['critical', 'high', 'failed', 'rejected', 'invalid', 'offline'].includes(status || ''))
    return 'red'
  if (
    [
      'stale',
      'warning',
      'medium',
      'timed_out',
      'expired',
      'degraded',
      'partial',
      'partial_estimate',
      'acknowledged_unverified',
      'insufficient_data',
      'unavailable',
      'estimated',
      'active',
      'open',
    ].includes(status || '')
  )
    return 'amber'
  if (
    ['SIMULATED', 'simulated', 'REPLAYED', 'acknowledged', 'evaluated', 'dispatched'].includes(
      status || '',
    )
  )
    return 'blue'
  return 'muted'
}
export function downloadJson(data: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' }),
  )
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
