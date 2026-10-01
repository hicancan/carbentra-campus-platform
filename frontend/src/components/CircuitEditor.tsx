import { IDENTIFIER_PATTERN } from '../lib/input-patterns'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { api, queryString } from '../lib/api'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Circuit, Topology } from '../lib/types'
import { Button, ErrorState, Field, Modal, Notice } from './ui'
import { BuildingFilter } from './Filters'
export default function CircuitEditor({
  circuit,
  onClose,
}: {
  circuit?: Circuit
  onClose: () => void
}) {
  const scope = useScope()
  const client = useQueryClient()
  const [id, setId] = useState(circuit?.id || '')
  const [name, setName] = useState(circuit?.name || '')
  const [campus, setCampus] = useState(
    circuit?.campus_id || scope.campusId || scope.campuses[0]?.id || '',
  )
  const [building, setBuilding] = useState(circuit?.building_id || '')
  const [parent, setParent] = useState(circuit?.parent_id || '')
  const [kind, setKind] = useState(circuit?.kind || 'branch')
  const [source, setSource] = useState(circuit?.source_mode || 'SIMULATED')
  const topology = useResource<Topology>(
    `/topology${queryString({ campus_id: campus, building_id: building })}`,
    { enabled: !!campus },
  )
  const mutation = useMutation({
    mutationFn: () =>
      circuit
        ? api.patch<Circuit>(`/circuits/${encodeURIComponent(circuit.id)}`, {
            name,
            parent_id: parent || null,
          })
        : api.post<Circuit>('/circuits', {
            id,
            name,
            campus_id: campus,
            building_id: building || null,
            parent_id: parent || null,
            kind,
            source_mode: source,
          }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal title={circuit ? '编辑回路' : '创建电气回路'} onClose={onClose}>
      <Notice title="保持历史计量边界">
        已有历史遥测的回路不能改变父级。需要调整边界时，创建新回路，再建立有时间记录的设备绑定。
      </Notice>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label="稳定回路 ID">
          <input
            required
            value={id}
            onChange={(e) => setId(e.target.value)}
            pattern={IDENTIFIER_PATTERN}
            maxLength={200}
            disabled={!!circuit}
          />
        </Field>
        <Field label="回路名称">
          <input required value={name} onChange={(e) => setName(e.target.value)} maxLength={200} />
        </Field>
        {!circuit && (
          <>
            <Field label="所属校区">
              <select
                value={campus}
                onChange={(e) => {
                  setCampus(e.target.value)
                  setBuilding('')
                  setParent('')
                }}
                required
              >
                <option value="">选择校区</option>
                {scope.campuses.map((c) => (
                  <option value={c.id} key={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="所属楼栋">
              <BuildingFilter
                campusId={campus}
                value={building}
                onChange={(id) => {
                  setBuilding(id)
                  setParent('')
                }}
                allLabel="校区级 / 无楼栋"
              />
            </Field>
            <div className="form-grid">
              <Field label="回路类型">
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="main">总进线</option>
                  <option value="branch">分支回路</option>
                  <option value="load">末端负载</option>
                </select>
              </Field>
              <Field label="来源模式">
                <select
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value as Circuit['source_mode'])
                    setParent('')
                  }}
                >
                  <option value="SIMULATED">SIMULATED</option>
                  <option value="REPLAYED">REPLAYED</option>
                  <option value="REAL">REAL</option>
                </select>
              </Field>
            </div>
          </>
        )}
        <Field label="父级回路" hint="只列出相同校区、楼栋与数据来源的候选父节点">
          <select value={parent} onChange={(e) => setParent(e.target.value)}>
            <option value="">无父级（根节点）</option>
            {topology.data?.circuits
              .filter(
                (c) =>
                  c.id !== id &&
                  c.campus_id === campus &&
                  (c.building_id || '') === building &&
                  c.source_mode === source,
              )
              .map((c) => (
                <option value={c.id} key={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
        </Field>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button type="button" onClick={onClose}>
            取消
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            <Save size={15} />
            {circuit ? '保存回路' : '创建回路'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
