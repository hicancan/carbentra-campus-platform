import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ClassroomTimeline from './ClassroomTimeline'
import { timelineFixture } from '../test-fixtures/classroom'
describe('historical classroom evidence', () => {
  it('shows unknown duration as an explicit interval and links genuine request events', () => {
    render(
      <MemoryRouter>
        <ClassroomTimeline data={timelineFixture()} />
      </MemoryRouter>,
    )
    expect(document.querySelectorAll('.room-interval-track .state-unknown')).toHaveLength(3)
    expect(screen.getByText('占用未知时长').parentElement).toHaveTextContent('59 分钟')
    expect(screen.getByText('功率未知时长').parentElement).toHaveTextContent('59 分钟')
    expect(screen.getByRole('link', { name: '命令详情' })).toHaveAttribute(
      'href',
      '/commands?command=command%3Atest%3A1',
    )
    expect(screen.getByText('待下发')).toBeVisible()
    expect(screen.queryByText('已验证')).toBeNull()
  })
  it('opens original observation IDs without synthesizing evidence for a gap', () => {
    render(
      <MemoryRouter>
        <ClassroomTimeline data={timelineFixture()} />
      </MemoryRouter>,
    )
    const group = screen.getByRole('group', { name: '实际占用历史时间线' })
    fireEvent.click(group.querySelectorAll('button')[1])
    expect(screen.getByText('原始观测 ID').parentElement).toHaveTextContent('无有效证据')
    expect(screen.getByText('观测功率').parentElement).toHaveTextContent('— W')
  })
})
