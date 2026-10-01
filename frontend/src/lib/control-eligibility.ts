import type { components } from './generated-api'
export type ControlEligibility = components['schemas']['ControlEligibilityResponse']
export type PhysicalConfirmation = components['schemas']['PhysicalConfirmation']
export type ControlAction = ControlEligibility['allowed_actions'][number]
export function physicalGateBlocker(
  eligibility: ControlEligibility,
  deviceId: string,
  receivedAt: number,
  now = Date.now(),
): string | null {
  if (eligibility.device_id !== deviceId) return '设备身份与授权检查不一致'
  if (eligibility.source_mode !== 'REAL') return '该路径仅用于真实设备的单独授权操作'
  if (eligibility.physical_deployment_enabled !== true) return '现场部署放行开关未启用'
  if (eligibility.dispatch_mode !== 'PHYSICAL') return '设备未配置独立现场执行通道'
  if (!eligibility.release || eligibility.release.status !== 'released')
    return '设备没有已放行的投运记录'
  if (!eligibility.load.id || !eligibility.load.name) return '未确认具体负载身份与名称'
  if (!Number.isSafeInteger(eligibility.profile_revision) || eligibility.profile_revision < 1)
    return '设备配置版本尚未核验'
  if (
    !Number.isFinite(receivedAt) ||
    receivedAt <= 0 ||
    now - receivedAt > 15_000 ||
    now < receivedAt - 1000
  )
    return '授权检查已过期，等待服务端重新检查'
  const checked = Date.parse(eligibility.checked_at),
    until = Date.parse(eligibility.release.valid_until)
  if (!Number.isFinite(checked) || !Number.isFinite(until) || until - checked <= now - receivedAt)
    return '设备放行记录已过期'
  if (eligibility.eligible !== true || !eligibility.allowed_actions.length)
    return '当前设备安全条件不允许执行'
  return null
}
export const controlReason = (reason?: string | null) =>
  ({
    physical_control_disabled: '现场放行条件未满足',
    read_only_channel: '此通道仅支持观测',
    historical_view: '历史快照不可控制',
    room_maintenance_interlock: '房间处于检修保护',
    room_fault_interlock: '房间处于故障闭锁',
    device_not_control_authorized: '设备尚未获得控制授权',
    stale_or_unknown_feedback: '输出反馈过期或未知',
    room_not_automatic: '房间尚未切换为自动模式',
    room_manual_mode: '房间处于人工模式',
    room_maintenance_mode: '房间处于检修模式',
    room_fault_mode: '房间处于故障闭锁模式',
    vacancy_not_persisted: '无人证据未持续达到阈值',
    target_binding_changed: '目标安装绑定已变化',
    load_not_observed_on: '未观测到输出开启',
    insufficient_known_power: '有效功率未达到阈值',
    bounded_command_limit: '达到本次命令数量上限',

    manual_override: '房间处于人工接管窗口',
    occupancy_unknown: '实际占用未知',
    occupied: '存在有效有人证据',
    vacancy_too_short: '持续无人时间不足',
    insufficient_vacancy: '持续无人证据不足',
    outside_policy_window: '不在策略生效窗口',
    policy_disabled: '策略已停用',
    minimum_power: '观测功率未达到策略阈值',

    control_not_authorized: '未授权控制',
    not_commissioned: '尚未投运',
    critical_load: '关键负载保护',
    unsupported_capability: '设备不支持此动作',
    maintenance_interlock: '处于检修保护窗口',
    stale_or_invalid_observation: '观测过期或无效',
    local_fault: '本地故障锁存',
    minimum_dwell: '未达到最小驻留时间',
    role_forbidden: '当前角色不可操作',
    unknown_requested_state: '目标输出状态未知',
  })[reason || ''] ||
  reason ||
  '允许'
export const controlActionLabel = (action: ControlAction) =>
  ({ hold: '保持当前状态', shed: '中断负载供电', restore: '恢复负载供电' })[action]
