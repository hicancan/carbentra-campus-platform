import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { classroomPath } from '../lib/classroom-display'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, Check, Download, FileUp, Plus, Search, Wrench, XCircle } from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Space } from '../lib/types'
import { browserTimezone } from '../lib/timezone'
import { downloadJson, formatDate, statusLabel } from '../lib/format'
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
  Loading,
  Modal,
  Notice,
  PageHeader,
  Pagination,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { BuildingFilter, PeriodFilter } from '../components/Filters'
export interface Schedule {
  id: string
  campus_id: string
  building_id: string | null
  space_id: string | null
  title: string
  kind: 'teaching' | 'holiday' | 'event' | 'maintenance'
  starts_at: string
  ends_at: string
  planned_occupancy: number | null
  observed_occupancy: 'unknown'
  source: string
  source_mode: 'SIMULATED' | 'REFERENCE'
  status: string
  revision: number
  created_at: string
  created_by: string
}
type ScheduleInput = Pick<
  Schedule,
  | 'campus_id'
  | 'building_id'
  | 'space_id'
  | 'title'
  | 'kind'
  | 'starts_at'
  | 'ends_at'
  | 'planned_occupancy'
  | 'source'
  | 'source_mode'
>
function defaultRange() {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  return { start: start.toISOString(), end: new Date(start.getTime() + 7 * 86400000).toISOString() }
}
function localTime(value: string) {
  const d = new Date(value)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
export function ScheduleForm({
  schedule,
  initialSpace,
  onClose,
}: {
  schedule?: Schedule
  initialSpace?: Pick<Space, 'id' | 'campus_id' | 'building_id'>
  onClose: () => void
}) {
  const scope = useScope()
  const client = useQueryClient()
  const [title, setTitle] = useState(schedule?.title || '')
  const [kind, setKind] = useState<Schedule['kind']>(schedule?.kind || 'teaching')
  const [campus, setCampus] = useState(
    schedule?.campus_id || initialSpace?.campus_id || scope.campusId || scope.campuses[0]?.id || '',
  )
  const [building, setBuilding] = useState(schedule?.building_id || initialSpace?.building_id || '')
  const [space, setSpace] = useState(schedule?.space_id || initialSpace?.id || '')
  const [start, setStart] = useState(localTime(schedule?.starts_at || new Date().toISOString()))
  const [end, setEnd] = useState(
    localTime(schedule?.ends_at || new Date(Date.now() + 3600000).toISOString()),
  )
  const [occupancy, setOccupancy] = useState(schedule?.planned_occupancy?.toString() || '')
  const [source, setSource] = useState(schedule?.source || '平台人工登记')
  const [mode, setMode] = useState<Schedule['source_mode']>(schedule?.source_mode || 'REFERENCE')
  const spaces = useResource<Space[]>(
    `/spaces${queryString({ building_id: building, limit: 500 })}`,
    { enabled: !!building },
  )
  const mutation = useMutation({
    mutationFn: () => {
      const body: ScheduleInput = {
        title,
        kind,
        campus_id: campus,
        building_id: building || null,
        space_id: space || null,
        starts_at: new Date(start).toISOString(),
        ends_at: new Date(end).toISOString(),
        planned_occupancy: occupancy === '' ? null : Number(occupancy),
        source,
        source_mode: mode,
      }
      return schedule
        ? api.put(`/schedules/${encodeURIComponent(schedule.id)}`, body)
        : api.post('/schedules', body)
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal title={schedule ? '编辑空间计划' : '登记空间计划'} onClose={onClose}>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label="计划标题">
          <input
            required
            value={title}
            maxLength={200}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="课程、活动、检修或节假日说明"
          />
        </Field>
        <div className="form-grid">
          <Field label="计划类型">
            <select value={kind} onChange={(e) => setKind(e.target.value as Schedule['kind'])}>
              {['teaching', 'event', 'maintenance', 'holiday'].map((k) => (
                <option key={k} value={k}>
                  {statusLabel(k)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="所属校区">
            <select
              required
              value={campus}
              onChange={(e) => {
                setCampus(e.target.value)
                setBuilding('')
                setSpace('')
              }}
            >
              <option value="">选择校区</option>
              {scope.campuses.map((c) => (
                <option value={c.id} key={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="楼栋范围">
          <BuildingFilter
            campusId={campus}
            value={building}
            onChange={(id) => {
              setBuilding(id)
              setSpace('')
            }}
            allLabel="整个校区"
          />
        </Field>
        <Field label="空间范围">
          <select value={space} onChange={(e) => setSpace(e.target.value)} disabled={!building}>
            <option value="">整个楼栋 / 校区</option>
            {spaces.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-grid">
          <Field label="计划开始">
            <input
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              max={end}
              required
            />
          </Field>
          <Field label="计划结束">
            <input
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              min={start}
              required
            />
          </Field>
        </div>
        <p className="timezone-hint">当前计划输入与显示时区：{browserTimezone()}</p>
        <Field label="计划人数（选填）" hint="留空表示未知；计划人数不会替代实际占用观测">
          <input
            type="number"
            min="0"
            max="100000"
            step="1"
            value={occupancy}
            onChange={(e) => setOccupancy(e.target.value)}
            placeholder="未知"
          />
        </Field>
        <div className="form-grid">
          <Field label="计划来源">
            <input
              required
              minLength={3}
              maxLength={500}
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </Field>
          <Field label="来源模式">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as Schedule['source_mode'])}
            >
              <option value="REFERENCE">REFERENCE · 参考计划</option>
              <option value="SIMULATED">SIMULATED · 模拟计划</option>
            </select>
          </Field>
        </div>
        <Notice tone={kind === 'maintenance' ? 'warning' : 'info'}>
          {kind === 'maintenance'
            ? '有效检修窗口会作为控制闭锁条件，不代替现场挂牌、隔离或验电。'
            : '计划未安排或节假日不代表房间无人，不能据此授权断电。'}
        </Notice>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button type="button" onClick={onClose}>
            取消
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            保存计划
          </Button>
        </div>
      </form>
    </Modal>
  )
}
function ImportSchedules({ onClose }: { onClose: () => void }) {
  const scope = useScope()
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [events, setEvents] = useState<ScheduleInput[] | null>(null)
  const [error, setError] = useState<string>('')
  const [filename, setFilename] = useState('')
  const mutation = useMutation({
    mutationFn: () => api.post<Schedule[]>('/schedules/import', { events }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const read = async (file?: File) => {
    if (!file) return
    setError('')
    mutation.reset()
    setEvents(null)
    if (file.size > 2 * 1024 * 1024) {
      setError('文件不能超过 2 MB')
      return
    }
    try {
      const parsed = JSON.parse(await file.text())
      const rows = Array.isArray(parsed) ? parsed : parsed.events
      if (!Array.isArray(rows) || !rows.length || rows.length > 500)
        throw new Error('必须包含 1–500 条计划')
      if (
        !rows.every(
          (r) =>
            r &&
            typeof r.title === 'string' &&
            typeof r.campus_id === 'string' &&
            ['teaching', 'event', 'maintenance', 'holiday'].includes(r.kind) &&
            r.starts_at &&
            r.ends_at &&
            ['SIMULATED', 'REFERENCE'].includes(r.source_mode),
        )
      )
        throw new Error('部分记录缺少必填字段或来源模式不正确')
      setEvents(rows)
      setFilename(file.name)
    } catch (e) {
      setError(e instanceof Error ? e.message : '无法读取 JSON 文件')
    }
  }
  return (
    <Modal title="批量导入参考计划" onClose={onClose}>
      <Notice>
        先在本地检查 JSON
        文件，再确认写入平台。服务端会校验所有计划的校区、空间、时间与权限，错误时整批不导入。
      </Notice>
      <div className="import-area">
        <FileUp size={32} />
        <h3>{filename || '选择计划 JSON 文件'}</h3>
        <p>支持 1–500 条，最大 2 MB</p>
        <input
          ref={input}
          type="file"
          accept=".json,application/json"
          aria-label="选择计划 JSON 文件"
          onChange={(e) => {
            void read(e.target.files?.[0])
          }}
        />
        <Button
          onClick={() =>
            downloadJson(
              {
                events: [
                  {
                    campus_id: scope.campusId || scope.campuses[0]?.id || 'campus-id',
                    building_id: null,
                    space_id: null,
                    title: '示例教学计划',
                    kind: 'teaching',
                    starts_at: new Date().toISOString(),
                    ends_at: new Date(Date.now() + 3600000).toISOString(),
                    planned_occupancy: null,
                    source: '待填写来源',
                    source_mode: 'REFERENCE',
                  },
                ],
              },
              'schedule-template.json',
            )
          }
        >
          <Download size={14} />
          下载模板
        </Button>
      </div>
      {error && (
        <p role="alert" className="validation-error">
          {error}
        </p>
      )}
      {events && (
        <>
          <p className="small section-space">已读取 {events.length} 条计划。以下预览前 5 条：</p>
          <DataTable
            rows={events.slice(0, 5)}
            rowKey={(r) => `${r.title}-${r.starts_at}`}
            columns={[
              { key: 'title', title: '标题', render: (r) => r.title },
              { key: 'kind', title: '类型', render: (r) => statusLabel(r.kind) },
              { key: 'start', title: '开始', render: (r) => formatDate(r.starts_at) },
            ]}
          />
        </>
      )}
      {mutation.error && <ErrorState error={mutation.error} />}
      {mutation.isSuccess ? (
        <Notice tone="success">已导入 {events?.length} 条计划，实际占用仍为未知</Notice>
      ) : (
        <div className="form-actions section-space">
          <Button onClick={onClose}>取消</Button>
          <Button
            variant="primary"
            disabled={!events}
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            <Check size={15} />
            确认导入 {events?.length || 0} 条
          </Button>
        </div>
      )}
    </Modal>
  )
}
export function ScheduleDetail({
  schedule,
  onClose,
  onEdit,
  readOnly = false,
}: {
  readOnly?: boolean
  schedule: Schedule
  onClose: () => void
  onEdit: () => void
}) {
  const auth = useAuth()
  const scope = useScope()
  const client = useQueryClient()
  const [note, setNote] = useState('')
  const cancel = useMutation({
    mutationFn: () => api.post(`/schedules/${encodeURIComponent(schedule.id)}/cancel`, { note }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Drawer title={schedule.title} subtitle={schedule.id} onClose={onClose}>
      <div className="inline-gap section-space">
        <Badge tone={schedule.kind === 'maintenance' ? 'amber' : 'blue'}>
          {statusLabel(schedule.kind)}
        </Badge>
        <StatusBadge value={schedule.status} />
        <Badge>{schedule.source_mode}</Badge>
      </div>
      <DefinitionList
        items={[
          [
            '校区',
            scope.campuses.find((c) => c.id === schedule.campus_id)?.name || schedule.campus_id,
          ],
          ['计划开始', formatDate(schedule.starts_at)],
          ['计划结束', formatDate(schedule.ends_at)],
          ['计划人数', schedule.planned_occupancy === null ? '未知' : schedule.planned_occupancy],
          ['实际占用', '计划不提供现场占用证据'],
          [
            '教室',
            schedule.space_id ? (
              <Link className="text-link" to={classroomPath(schedule.space_id)}>
                打开教室工作台
              </Link>
            ) : (
              '校区或楼栋级计划'
            ),
          ],
          ['来源', schedule.source],
          ['修订版本', schedule.revision],
          ['登记人员', schedule.created_by],
        ]}
      />
      <Notice tone={schedule.kind === 'maintenance' ? 'warning' : 'info'}>
        {schedule.kind === 'maintenance'
          ? '当前有效检修窗口会阻止控制调度。取消计划不会代替现场检修结束验收。'
          : '教学或活动安排是参考计划。未安排不等于无人，计划人数不等于实测人数。'}
      </Notice>
      {!readOnly &&
        permissions.operate(auth.session?.user.role) &&
        schedule.status !== 'cancelled' && (
          <>
            <Button onClick={onEdit}>编辑计划</Button>
            <form
              className="form-stack cancel-schedule"
              onSubmit={(e) => {
                e.preventDefault()
                cancel.mutate()
              }}
            >
              <Field label="取消原因">
                <textarea
                  minLength={3}
                  maxLength={2000}
                  required
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="记录取消此计划的原因…"
                />
              </Field>
              {cancel.error && <ErrorState error={cancel.error} compact />}
              <Button variant="danger" type="submit" loading={cancel.isPending}>
                <XCircle size={15} />
                取消计划并留存记录
              </Button>
            </form>
          </>
        )}
    </Drawer>
  )
}
export default function Schedules() {
  const auth = useAuth()
  const scope = useScope()
  const [params] = useSearchParams()
  const selectedSpace = params.get('space') || ''
  const [range, setRange] = useState(defaultRange)
  const [building, setBuilding] = useState(params.get('building') || '')
  useEffect(() => setBuilding(params.get('building') || ''), [params])
  const [kind, setKind] = useState('')
  const [view, setView] = useState('agenda')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<Schedule | null>(null)
  const [editing, setEditing] = useState<Schedule | undefined>()
  const [create, setCreate] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const query = useCollection<Schedule>(
    `/schedules${queryString({ campus_id: scope.campusId, building_id: building, space_id: selectedSpace, ...range, limit: 500, offset })}`,
  )
  const rows = useMemo(
    () =>
      (query.data?.data || []).filter(
        (s) => (!kind || s.kind === kind) && s.title.toLowerCase().includes(search.toLowerCase()),
      ),
    [query.data, kind, search],
  )
  const days = useMemo(
    () => [...new Set(rows.map((r) => new Date(r.starts_at).toLocaleDateString('zh-CN')))],
    [rows],
  )
  const close = useCallback(() => setSelected(null), [])
  const closeForm = useCallback(() => {
    setCreate(false)
    setEditing(undefined)
  }, [])
  const closeImport = useCallback(() => setImportOpen(false), [])
  return (
    <>
      <PageHeader
        eyebrow="CAMPUS CALENDAR"
        title="空间计划与检修"
        description="关联课程、活动、节假日与检修窗口；计划与现场占用保持清晰分离。"
        actions={
          permissions.operate(auth.session?.user.role) && (
            <>
              <Button onClick={() => setImportOpen(true)}>
                <FileUp size={15} />
                导入计划
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setEditing(undefined)
                  setCreate(true)
                }}
              >
                <Plus size={15} />
                登记计划
              </Button>
            </>
          )
        }
      />
      {selectedSpace && (
        <Notice>
          当前展示指定教室的计划 ·{' '}
          <Link className="text-link" to={classroomPath(selectedSpace)}>
            返回教室工作台
          </Link>
        </Notice>
      )}
      <div className="filter-bar">
        <BuildingFilter
          value={building}
          onChange={(id) => {
            setBuilding(id)
            setOffset(0)
          }}
        />
        <PeriodFilter
          value={range}
          onChange={(r) => {
            setRange(r)
            setOffset(0)
          }}
        />
      </div>
      <Notice title="计划不是占用传感器">
        无课程、节假日或计划人数为零，均不授权设备断电。检修窗口仅作为安全闭锁条件，不证明现场已经隔离。
      </Notice>
      <Card>
        <CardHeader
          title="近期空间安排"
          subtitle="按计划开始时间排列；已取消安排仍保留历史记录"
          actions={<Badge>{Number(query.data?.meta?.total || 0)} 条计划</Badge>}
        />
        <Tabs
          active={view}
          onChange={setView}
          items={[
            { id: 'agenda', label: '日程视图' },
            { id: 'list', label: '计划清单' },
          ]}
        />
        <div className="filter-bar table-filters">
          <label className="search-field">
            <Search size={15} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="搜索计划"
              placeholder="搜索计划标题…"
            />
          </label>
          <select aria-label="计划类型" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">全部类型</option>
            {['teaching', 'event', 'maintenance', 'holiday'].map((k) => (
              <option key={k} value={k}>
                {statusLabel(k)}
              </option>
            ))}
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
        ) : !rows.length ? (
          <EmptyState
            title="此时间范围暂无匹配计划"
            description="没有计划不表示房间空闲；实际占用仍未知"
            icon={<CalendarDays size={30} />}
          />
        ) : view === 'agenda' ? (
          <div className="agenda">
            {days.map((day) => (
              <div className="agenda-day" key={day}>
                <div className="agenda-date">
                  <CalendarDays size={17} />
                  <strong>{day}</strong>
                </div>
                <div>
                  {rows
                    .filter((r) => new Date(r.starts_at).toLocaleDateString('zh-CN') === day)
                    .map((r) => (
                      <button
                        key={r.id}
                        className={`agenda-event ${r.status === 'cancelled' ? 'cancelled' : ''}`}
                        onClick={() => setSelected(r)}
                      >
                        <span className={`agenda-kind kind-${r.kind}`}>
                          {r.kind === 'maintenance' ? (
                            <Wrench size={18} />
                          ) : (
                            <CalendarDays size={18} />
                          )}
                        </span>
                        <div>
                          <strong>{r.title}</strong>
                          <small>
                            {formatDate(r.starts_at)} → {formatDate(r.ends_at)}
                          </small>
                        </div>
                        <Badge tone={r.kind === 'maintenance' ? 'amber' : 'blue'}>
                          {statusLabel(r.kind)}
                        </Badge>
                        <StatusBadge value={r.status} />
                        <span className="agenda-occupancy">占用未知</span>
                      </button>
                    ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <DataTable
            rows={rows}
            rowKey={(r) => r.id}
            onRowClick={setSelected}
            columns={[
              { key: 'title', title: '计划标题', render: (r) => <strong>{r.title}</strong> },
              { key: 'kind', title: '类型', render: (r) => statusLabel(r.kind) },
              { key: 'start', title: '开始', render: (r) => formatDate(r.starts_at) },
              { key: 'end', title: '结束', render: (r) => formatDate(r.ends_at) },
              { key: 'status', title: '状态', render: (r) => <StatusBadge value={r.status} /> },
              { key: 'source', title: '来源模式', render: (r) => <Badge>{r.source_mode}</Badge> },
              { key: 'occupancy', title: '占用', render: () => '未知' },
            ]}
          />
        )}
        {Number(query.data?.meta?.total || 0) > 500 && (
          <Pagination
            offset={offset}
            limit={500}
            total={Number(query.data?.meta?.total)}
            setOffset={setOffset}
          />
        )}
      </Card>
      {selected && (
        <ScheduleDetail
          schedule={selected}
          onClose={close}
          onEdit={() => {
            setEditing(selected)
            setSelected(null)
            setCreate(true)
          }}
        />
      )}
      {create && <ScheduleForm schedule={editing} onClose={closeForm} />}
      {importOpen && <ImportSchedules onClose={closeImport} />}
    </>
  )
}
