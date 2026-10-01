const messages: Record<string, string> = {
  rule_revision_conflict: '规则已由其他操作更新，请读取最新版本后重新复核',
  stale_rule_revision: '规则版本已变化，请读取最新配置后再提交',
  channel_required: '此设备必须选择明确继电器通道，不能整机操作',
  channel_target_required: '此设备必须选择明确继电器通道，不能整机操作',
  invalid_window: '请选择有效时间区间，单次查询或策略窗口最多 7 天',
  timeline_too_dense: '此区间的变化事件过密，请缩短时间范围后重试',
  policy_stale: '策略版本已变化，请重新评估后再执行',
  evaluation_expired: '评估超过 30 秒或策略已变化，请重新评估',
  no_eligible_targets: '新观测已不允许执行，请查看最新评估依据',
  policy_scope_mismatch: '目标通道与当前教室安装绑定不一致',
  shadow_only: '影子评估不会执行控制命令',
  evaluation_stale: '评估已经过期，请重新评估当前条件',
  room_maintenance_interlock: '房间处于检修保护，控制保持关闭',
  room_fault_interlock: '房间故障闭锁尚未解除，控制保持关闭',
  invalid_credentials: '账户或密码不正确，请检查后重试',
  unauthenticated: '会话已失效，请重新登录',
  unauthorized: '会话未建立或已失效，请重新登录',
  rate_limited: '尝试次数较多，请稍后再试',
  forbidden: '当前角色无权执行此操作',
  scope_forbidden: '当前账户无权访问所选校区或资源',
  scope_denied: '当前账户无权访问所选校区或资源',
  global_administrator_required: '此项全校区配置仅允许全局管理员修改',
  csrf_failed: '安全校验未通过，请刷新会话后重新操作',
  not_found: '资源不存在或不在当前访问范围内',
  already_exists: '该稳定标识已存在，请先查看已有档案',
  validation_error: '部分输入不符合要求，请检查下方字段提示',
  invalid_request: '部分输入不符合要求，请检查下方字段提示',
  binding_mismatch: '校区、楼栋、楼层、空间或回路的绑定关系不一致',
  source_mode_mismatch: '设备与计量边界的数据来源模式不一致',
  stale_or_invalid_observation: '设备观测过期或无效，已阻止控制操作',
  stale_observation: '设备观测已过期，等待有效的新观测后再操作',
  physical_control_disabled: '现场控制条件尚未放行，操作已阻止',
  physical_review_stale: '放行记录或设备配置已变化，请重新读取资格并复核负载',
  physical_confirmation_required: '请重新核对设备、明确负载、动作与市电后果后确认',
  critical_load: '关键负载受到保护，不能启用自动控制',
  not_commissioned: '设备尚未投运，控制保持关闭',
  maintenance_interlock: '设备处于检修保护时段，控制保持关闭',
  command_in_flight: '已有命令执行中，请先查看命令追踪',
  unknown_requested_state: '输出目标状态未知，无法执行保持动作',
  idempotency_conflict: '此请求标识已对应另一组参数，请先核对命令追踪中的原请求',
}
export function apiErrorMessage(code: string, status: number, technicalMessage: string) {
  if (Object.hasOwn(messages, code)) return messages[code]
  if (status === 429) return messages.rate_limited
  if (status === 401) return messages.unauthorized
  if (status === 403) return messages.forbidden
  if (status === 504) return '服务响应超时，请稍后重试'
  if (status === 502 || status === 503) return '服务暂时不可用，请稍后重试'
  return technicalMessage
}
