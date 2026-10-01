/** Keep telemetry bursts from invalidating static registries or retraining forecasts. */
export function eventResourcePrefixes(type: string): string[] {
  if (type.startsWith('telemetry.'))
    return [
      '/classrooms',
      '/overview',
      '/devices',
      '/telemetry',
      '/energy/',
      '/carbon/summary',
      '/cost/summary',
      '/system/status',
    ]
  if (type.startsWith('command.'))
    return ['/classrooms', '/commands', '/devices', '/audit', '/system/status']
  if (type.startsWith('alarm.')) return ['/classrooms', '/alarms', '/overview', '/audit']
  if (type.startsWith('strategy.')) return ['/strategies', '/commands', '/audit']
  if (type.startsWith('device.') || type.startsWith('circuit.'))
    return ['/devices', '/topology', '/buildings', '/overview', '/audit']
  if (type.startsWith('schedule.')) return ['/classrooms', '/schedules', '/strategies', '/audit']
  if (
    type.startsWith('classroom.') ||
    type.startsWith('channel.') ||
    type.startsWith('room.') ||
    type.startsWith('room_policy.') ||
    type.startsWith('room_evaluation.') ||
    type.startsWith('room_anomaly.')
  )
    return ['/classrooms', '/devices', '/commands', '/audit']
  if (type.startsWith('report.')) return ['/reports', '/audit']
  if (type.startsWith('user.')) return ['/users', '/audit']
  if (type.startsWith('settings.'))
    return ['/settings', '/system/status', '/devices', '/overview', '/audit']
  return []
}
