import { BarChart3, BrainCircuit, Clock3, Layers3 } from 'lucide-react'
import { formatDate, formatNumber } from '../lib/format'
import type { Forecast } from '../lib/types'
import { Badge, DataTable, DefinitionList, Notice, StatusBadge } from './ui'
export default function ForecastEvidence({ forecast: d }: { forecast: Forecast }) {
  if (!d.model) return null
  const rows = d.holdout
    ? Object.entries(d.holdout.models).map(([method, scores]) => ({ method, ...scores }))
    : []
  return (
    <div className="forecast-evidence">
      <div className="forecast-quality-grid">
        <div>
          <BrainCircuit size={17} />
          <span>当前选用</span>
          <strong>{d.method === 'ridge_regression' ? '岭回归模型' : '季节性基线'}</strong>
          <small>{d.model.trained ? '模型已训练，按验证集比较选择' : '历史样本不足'}</small>
        </div>
        <div>
          <Layers3 size={17} />
          <span>计量设备覆盖</span>
          <strong>
            {d.coverage?.eligible_device_count ?? '—'} / {d.coverage?.selected_device_count ?? '—'}
          </strong>
          <small>固定合格计量队列，不补齐缺测设备</small>
        </div>
        <div>
          <BarChart3 size={17} />
          <span>保留测试样本</span>
          <strong>
            {d.holdout?.sample_count ?? '—'}
            <small>小时</small>
          </strong>
          <small>与训练与模型选择数据分离</small>
        </div>
        <div>
          <Clock3 size={17} />
          <span>观测新鲜度</span>
          <StatusBadge value={d.freshness?.status} />
          <small>最近观测 {formatDate(d.freshness?.latest_sample_at)}</small>
        </div>
      </div>
      <details className="forecast-details">
        <summary>
          模型选择与独立测试证据 <Badge>{d.model.version}</Badge>
        </summary>
        <div className="forecast-detail-body">
          <Notice title="依据比较选择模型">
            {d.model.selection_reason}。预测不是现场实测，也不保证未来误差。简单基线更好时保留基线。
          </Notice>
          <DataTable
            rows={rows}
            rowKey={(r) => r.method}
            columns={[
              {
                key: 'model',
                title: '预测方法',
                render: (r) => (
                  <strong>
                    {r.method === 'ridge_regression' ? '岭回归' : '季节性朴素基线'}{' '}
                    {d.method === r.method && <Badge tone="teal">已选用</Badge>}
                  </strong>
                ),
              },
              { key: 'mae', title: '独立测试 MAE / kW', render: (r) => formatNumber(r.mae_kw, 3) },
              {
                key: 'rmse',
                title: '独立测试 RMSE / kW',
                render: (r) => formatNumber(r.rmse_kw, 3),
              },
            ]}
          />
          <DefinitionList
            items={[
              ['训练样本', d.model.training_sample_count],
              [
                '选模验证区间',
                d.model.validation
                  ? `${formatDate(d.model.validation.start)} – ${formatDate(d.model.validation.end)}`
                  : '不足',
              ],
              [
                '独立测试区间',
                d.holdout
                  ? `${formatDate(d.holdout.start)} – ${formatDate(d.holdout.end)}`
                  : '不足',
              ],
              ['预测起点', formatDate(d.model.prediction_origin)],
              ['日历时区', d.model.calendar_timezone || '—'],
              ['区间方法', d.holdout?.band?.method || '—'],
              [
                '全范围覆盖',
                d.coverage?.scope_complete ? '完整合格队列' : '部分范围；有设备或小时被排除',
              ],
            ]}
          />
          {d.coverage?.excluded_devices?.length ? (
            <>
              <h3 className="section-title">被排除的计量设备</h3>
              <DataTable
                rows={d.coverage.excluded_devices}
                rowKey={(r) => r.device_id}
                columns={[
                  { key: 'device', title: '设备', render: (r) => r.device_id },
                  { key: 'reason', title: '原因', render: (r) => r.reasons.join('；') },
                ]}
              />
            </>
          ) : null}
        </div>
      </details>
    </div>
  )
}
