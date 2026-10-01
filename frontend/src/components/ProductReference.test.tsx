import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ProductReference from './ProductReference'
const canvas = vi.hoisted(() => vi.fn())
const refetch = vi.hoisted(() => vi.fn())
const productState = vi.hoisted(() => ({ family: 'PLUG', paths: [] as string[] }))
vi.mock('../lib/hooks', () => ({
  useResource: (path: string) => {
    productState.paths.push(path)
    return {
      data: {
        family: productState.family,
        version: 'rev-b',
        bytes: 30337768,
        node_count: 227,
        triangle_count: 666556,
        parts: [],
        optimized: false,
        units: 'm',
        source_commit: 'fixture',
        source_sha256: '0'.repeat(64),
        display_sha256: '1'.repeat(64),
      },
      isLoading: false,
      isFetching: false,
      refetch,
      error: null,
    }
  },
}))
vi.mock('./ProductCanvas', () => ({
  default: () => {
    canvas()
    return <div>Explicitly loaded product canvas</div>
  },
}))
beforeEach(() => {
  canvas.mockClear()
  refetch.mockClear()
  productState.family = 'PLUG'
  productState.paths = []
})
describe('optional product display', () => {
  it('does not instantiate the heavy viewer until the user explicitly asks', async () => {
    render(<ProductReference family="PLUG" />)
    expect(canvas).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '刷新发布资料' }))
    expect(refetch).toHaveBeenCalledOnce()
    expect(screen.queryByText('Explicitly loaded product canvas')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '加载三维参考模型' }))
    await screen.findByText('Explicitly loaded product canvas')
    expect(canvas).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '卸载模型' }))
    expect(screen.queryByText('Explicitly loaded product canvas')).toBeNull()
    expect(screen.getByRole('button', { name: '加载三维参考模型' })).toBeVisible()
  })
  it('unknown hardware does not silently display the Plug reference', () => {
    render(<ProductReference family={null} />)
    expect(screen.getByText('此设备没有已核验的产品参考类型')).toBeVisible()
    expect(screen.queryByRole('button', { name: '加载三维参考模型' })).toBeNull()
    expect(productState.paths).toHaveLength(0)
  })
  it('changing family requires a new explicit 3D load action', async () => {
    const view = render(<ProductReference family="PLUG" />)
    fireEvent.click(screen.getByRole('button', { name: '加载三维参考模型' }))
    await screen.findByText('Explicitly loaded product canvas')
    productState.family = 'SWITCH'
    view.rerender(<ProductReference family="SWITCH" />)
    expect(screen.queryByText('Explicitly loaded product canvas')).toBeNull()
    expect(screen.getByRole('button', { name: '加载三维参考模型' })).toBeVisible()
    expect(productState.paths).toContain('/assets/product/manifest?family=SWITCH')
  })
  it('rejects a published reference whose family does not match the requested device', () => {
    render(<ProductReference family="PRESENCE" />)
    expect(screen.getByText('产品参考清单与所选类型不一致，模型未加载')).toBeVisible()
    expect(screen.queryByRole('button', { name: '加载三维参考模型' })).toBeNull()
  })
})
