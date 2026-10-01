import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Classrooms from './Classrooms'
import { roomFixture } from '../test-fixtures/classroom'
const context = vi.hoisted(() => ({
  paths: [] as string[],
  rows: [] as ReturnType<typeof roomFixture>[],
  floors: [] as { id: string; name: string; level: number }[],
}))
vi.mock('../lib/scope', () => ({ useScope: () => ({ campusId: 'campus:test', campuses: [] }) }))
vi.mock('../lib/hooks', () => ({
  useCollection: (path: string) => {
    context.paths.push(path)
    return { isLoading: false, data: { data: context.rows, meta: { total: context.rows.length } } }
  },
  useResource: (path: string) => ({
    isLoading: false,
    data: path.startsWith('/floors')
      ? context.floors
      : [{ id: 'building:test', name: '教学楼', campus_id: 'campus:test' }],
  }),
}))
beforeEach(() => {
  context.paths = []
  context.floors = []
  context.rows = [roomFixture({ channels: [] })]
})
describe('campus-wide classroom matrix', () => {
  it('requests a campus-scoped all-room limit and never defaults unknown to vacant', () => {
    render(
      <MemoryRouter>
        <Classrooms />
      </MemoryRouter>,
    )
    expect(context.paths[0]).toContain('campus_id=campus%3Atest')
    expect(context.paths[0]).toContain('limit=2000')
    expect(screen.getByRole('link', { name: '教学楼101，未知，打开教室' })).toHaveAttribute(
      'href',
      '/classrooms/space%3Atest%3A101',
    )
    expect(screen.getByText('功率未知 · 0 通道')).toBeVisible()
  })
  it('preserves timestamp through deep links and state filters', () => {
    render(
      <MemoryRouter initialEntries={['/classrooms?at=2026-10-01T04%3A00%3A00Z']}>
        <Classrooms />
      </MemoryRouter>,
    )
    expect(context.paths[0]).toContain('at=2026-10-01T04%3A00%3A00.000Z')
    expect(
      screen.getByRole('link', { name: '教学楼101，未知，打开教室' }).getAttribute('href'),
    ).toContain('at=')
    fireEvent.change(screen.getByRole('combobox', { name: '筛选房间状态' }), {
      target: { value: 'vacant' },
    })
    expect(screen.getByText('没有匹配的空间')).toBeVisible()
    expect(screen.queryByRole('link', { name: '教学楼101，无人，打开教室' })).toBeNull()
  })
  it('orders floor rows by signed metadata level, then name, with deterministic unknowns last', () => {
    context.floors = [
      { id: 'floor:a', name: '4层', level: 4 },
      { id: 'floor:b', name: '2层', level: 2 },
      { id: 'floor:c', name: '5层', level: 5 },
      { id: 'floor:d', name: '1层', level: 1 },
      { id: 'floor:e', name: '3层', level: 3 },
      { id: 'floor:f', name: '地下1层', level: -1 },
      { id: 'floor:g', name: '地下2层', level: -2 },
      { id: 'floor:h', name: '地面层', level: 0 },
      { id: 'floor:i', name: '夹层10', level: 1.5 },
      { id: 'floor:j', name: '夹层2', level: 1.5 },
    ]
    context.rows = [
      ...context.floors.map((floor) => floor.id),
      'floor:unknown-z',
      'floor:unknown-a',
    ].map((floor_id, index) =>
      roomFixture({ id: `space:${index}`, name: `空间${index}`, floor_id, channels: [] }),
    )
    const { container } = render(
      <MemoryRouter>
        <Classrooms />
      </MemoryRouter>,
    )
    expect(
      [...container.querySelectorAll('.room-floor-label')].map((label) => label.textContent),
    ).toEqual([
      '地下2层',
      '地下1层',
      '地面层',
      '1层',
      '夹层2',
      '夹层10',
      '2层',
      '3层',
      '4层',
      '5层',
      'a',
      'z',
    ])
  })
  it('retains all 603 mapped rooms with bounded DOM pagination rather than truncating at500', () => {
    context.rows = Array.from({ length: 603 }, (_, index) =>
      roomFixture({ id: `space:test:${index}`, name: `空间${index}`, channels: [] }),
    )
    render(
      <MemoryRouter>
        <Classrooms />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('link', { name: /打开教室$/ })).toHaveLength(96)
    for (let page = 0; page < 6; page++)
      fireEvent.click(screen.getByRole('button', { name: '下一页' }))
    expect(screen.getAllByRole('link', { name: /打开教室$/ })).toHaveLength(27)
    expect(screen.getByRole('link', { name: '空间602，未知，打开教室' })).toBeVisible()
  })
})
