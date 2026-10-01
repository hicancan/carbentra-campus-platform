import { Plus, X } from 'lucide-react'
import type { DraftRateBand } from '../lib/pricing'
import { parseRateBands } from '../lib/pricing'
import { Button, IconButton, Notice } from './ui'
export default function TariffBands({
  value,
  onChange,
  currency,
}: {
  value: DraftRateBand[]
  onChange: (value: DraftRateBand[]) => void
  currency: string
}) {
  const change = (key: string, patch: Partial<DraftRateBand>) =>
    onChange(value.map((row) => (row.key === key ? { ...row, ...patch } : row)))
  const validation = parseRateBands(value)
  return (
    <div className="tariff-band-editor">
      <div className="inline-between">
        <strong>每日分时覆盖（选填）</strong>
        <Button
          disabled={value.length >= 24}
          onClick={() =>
            onChange([
              ...value,
              { key: crypto.randomUUID(), start: '00:00', end: '24:00', rate: '', label: '' },
            ])
          }
        >
          <Plus size={13} />
          增加时段
        </Button>
      </div>
      <p>区间内覆盖基础单价；未覆盖时段沿用基础单价。跨午夜请拆成两行。</p>
      {value.map((row, index) => (
        <div className="tariff-band-row" key={row.key}>
          <label>
            标签
            <input
              aria-label={`时段 ${index + 1} 标签`}
              value={row.label}
              onChange={(e) => change(row.key, { label: e.target.value })}
              maxLength={80}
              placeholder="峰 / 谷 / 平"
            />
          </label>
          <label>
            开始
            <input
              aria-label={`时段 ${index + 1} 开始`}
              value={row.start}
              onChange={(e) => change(row.key, { start: e.target.value })}
              inputMode="numeric"
              maxLength={5}
              placeholder="00:00"
              required
            />
          </label>
          <label>
            结束
            <input
              aria-label={`时段 ${index + 1} 结束`}
              value={row.end}
              onChange={(e) => change(row.key, { end: e.target.value })}
              inputMode="numeric"
              maxLength={5}
              placeholder="24:00"
              required
            />
          </label>
          <label>
            {currency}/kWh
            <input
              aria-label={`时段 ${index + 1} 单价`}
              type="number"
              min="0"
              max="1000"
              step="0.000001"
              value={row.rate}
              onChange={(e) => change(row.key, { rate: e.target.value })}
              required
            />
          </label>
          <IconButton
            label={`删除时段 ${index + 1}`}
            onClick={() => onChange(value.filter((v) => v.key !== row.key))}
          >
            <X size={14} />
          </IconButton>
        </div>
      ))}
      {validation.error && (
        <p className="validation-error" role="alert">
          {validation.error}
        </p>
      )}
      {value.length > 0 && (
        <Notice>
          时段使用电价指定的 IANA
          日历时区。夏令时跳变存在歧义时，服务端会返回不可定价，避免静默猜测。
        </Notice>
      )}
    </div>
  )
}
