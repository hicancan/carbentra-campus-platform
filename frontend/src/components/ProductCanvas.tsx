import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { Focus, Maximize2 } from 'lucide-react'
import type { ProductManifest } from '../lib/product'
import { loadVerifiedProduct } from '../lib/product'
import { ErrorState, IconButton, Loading } from './ui'
interface ModelRuntime {
  select: (id: string, isolate: boolean) => void
  reset: () => void
  focus: (id: string) => void
}
function disposeObjects(scene: THREE.Object3D) {
  const materials = new Set<THREE.Material>(),
    textures = new Set<THREE.Texture>()
  scene.traverse((object) => {
    if (!(object instanceof THREE.Mesh || object instanceof THREE.LineSegments)) return
    object.geometry.dispose()
    for (const material of Array.isArray(object.material) ? object.material : [object.material])
      materials.add(material)
  })
  for (const material of materials) {
    for (const value of Object.values(material))
      if (value instanceof THREE.Texture) textures.add(value)
    material.dispose()
  }
  for (const texture of textures) texture.dispose()
}
export default function ProductCanvas({
  manifest,
  selected,
  isolate,
  rotate,
  onSelect,
}: {
  manifest: ProductManifest
  selected: string
  isolate: boolean
  rotate: boolean
  onSelect: (id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null),
    runtime = useRef<ModelRuntime | null>(null),
    controlsRef = useRef<OrbitControls | null>(null)
  const current = useRef({ selected, isolate, onSelect })
  current.current = { selected, isolate, onSelect }
  const [progress, setProgress] = useState(0),
    [phase, setPhase] = useState('读取与校验产物'),
    [loading, setLoading] = useState(true),
    [error, setError] = useState<unknown>(null)
  useEffect(() => {
    runtime.current?.select(selected, isolate)
  }, [selected, isolate])
  useEffect(() => {
    if (controlsRef.current) controlsRef.current.autoRotate = rotate
  }, [rotate])
  useEffect(() => {
    if (!container.current) return
    const host = container.current,
      abort = new AbortController()
    let disposed = false,
      frame = 0,
      dirty = true
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true })
    } catch {
      setError(new Error('当前浏览器无法启用 WebGL，产品资料与设备遥测仍可查看'))
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    setProgress(0)
    setPhase('读取与校验产物')
    renderer.setSize(host.clientWidth, host.clientHeight)
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.25
    host.appendChild(renderer.domElement)
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#edf1ea')
    const camera = new THREE.PerspectiveCamera(
      38,
      host.clientWidth / host.clientHeight,
      0.0001,
      100,
    )
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.autoRotateSpeed = 1.1
    controlsRef.current = controls
    const changed = () => {
      dirty = true
    }
    controls.addEventListener('change', changed)
    const room = new RoomEnvironment()
    const pmrem = new THREE.PMREMGenerator(renderer)
    const environment = pmrem.fromScene(room, 0.04)
    room.dispose()
    pmrem.dispose()
    scene.environment = environment.texture
    scene.add(new THREE.HemisphereLight('#ffffff', '#b6c0b1', 2))
    const light = new THREE.DirectionalLight('#ffffff', 2.5)
    light.position.set(-1, 2, 3)
    scene.add(light)
    const parts = new Map<string, THREE.Object3D>(),
      pickable: THREE.Mesh[] = []
    let outline: THREE.BoxHelper | null = null
    const applySelection = (id: string, solo: boolean) => {
      for (const [partId, part] of parts) part.visible = !solo || !id || partId === id
      if (outline) {
        scene.remove(outline)
        outline.geometry.dispose()
        ;(outline.material as THREE.Material).dispose()
        outline = null
      }
      const part = parts.get(id)
      if (part) {
        outline = new THREE.BoxHelper(part, '#298568')
        scene.add(outline)
      }
      dirty = true
    }
    void (async () => {
      try {
        const buffer = await loadVerifiedProduct(manifest, abort.signal, (value) => {
          if (!disposed) setProgress(value)
        })
        if (disposed) return
        setPhase('生成产品视图')
        const manager = new THREE.LoadingManager()
        manager.setURLModifier((url) => {
          if (url.startsWith('blob:') || url.startsWith('data:')) return url
          throw new Error('产品显示件必须为自包含 GLB，已阻止外部资源请求')
        })
        const loader = new GLTFLoader(manager)
        const gltf = await loader.parseAsync(buffer, '/api/v1/assets/product/')
        if (disposed) {
          disposeObjects(gltf.scene)
          return
        }
        const sourceNodes = (gltf.parser.json.nodes || []) as { name?: string }[]
        const manifestParts = new Set(manifest.parts.map((part) => part.id))
        gltf.scene.traverse((object) => {
          const nodeIndex = gltf.parser.associations.get(object)?.nodes
          const sourceName = nodeIndex === undefined ? undefined : sourceNodes[nodeIndex]?.name
          if (sourceName && manifestParts.has(sourceName)) {
            object.userData.productPartId = sourceName
            parts.set(sourceName, object)
          }
          if (object instanceof THREE.Mesh) pickable.push(object)
        })
        if (
          !parts.size ||
          parts.size !== manifestParts.size ||
          manifestParts.size !== manifest.parts.length ||
          !pickable.length
        ) {
          disposeObjects(gltf.scene)
          throw new Error('产品节点身份与固定清单不匹配，已停止展示')
        }
        scene.add(gltf.scene)
        const bounds = new THREE.Box3().setFromObject(gltf.scene),
          center = bounds.getCenter(new THREE.Vector3()),
          size = bounds.getSize(new THREE.Vector3()),
          span = Math.max(size.x, size.y, size.z)
        if (!Number.isFinite(span) || span <= 0) throw new Error('产品模型没有有效显示边界')
        controls.minDistance = span * 0.4
        controls.maxDistance = span * 8
        camera.near = Math.max(span / 1000, 0.00001)
        camera.far = span * 50
        camera.updateProjectionMatrix()
        const reset = () => {
          controls.minDistance = span * 0.4
          controls.target.copy(center)
          camera.position.set(center.x + span * 1.4, center.y + span * 0.8, center.z + span * 1.9)
          controls.update()
          dirty = true
        }
        const focus = (id: string) => {
          const part = parts.get(id)
          if (!part) return
          const partBounds = new THREE.Box3().setFromObject(part),
            partCenter = partBounds.getCenter(new THREE.Vector3()),
            partSize = partBounds.getSize(new THREE.Vector3())
          const partSpan = Math.max(partSize.x, partSize.y, partSize.z)
          if (!Number.isFinite(partSpan) || partSpan <= 0) return
          const direction = camera.position.clone().sub(controls.target).normalize()
          controls.minDistance = Math.max(partSpan * 0.25, span * 0.015)
          controls.target.copy(partCenter)
          camera.position
            .copy(partCenter)
            .addScaledVector(direction, Math.max(partSpan * 2.8, span * 0.07))
          controls.update()
          dirty = true
        }
        runtime.current = { select: applySelection, reset, focus }
        reset()
        applySelection(current.current.selected, current.current.isolate)
        setLoading(false)
        dirty = true
      } catch (e) {
        if (!disposed && !(e instanceof DOMException && e.name === 'AbortError')) {
          setError(e)
          setLoading(false)
        }
      }
    })()
    const raycaster = new THREE.Raycaster(),
      pointer = new THREE.Vector2()
    let down = { x: 0, y: 0 }
    const pointerDown = (event: PointerEvent) => {
      down = { x: event.clientX, y: event.clientY }
    }
    const pointerUp = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - down.x, event.clientY - down.y) > 5) return
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(pointer, camera)
      const hits = raycaster.intersectObjects(pickable, false)
      for (const hit of hits) {
        let object: THREE.Object3D | null = hit.object
        let visible = true
        let partId = ''
        while (object) {
          if (!object.visible) visible = false
          if (object.userData.productPartId) partId = object.userData.productPartId
          object = object.parent
        }
        if (visible && partId) {
          current.current.onSelect(partId)
          break
        }
      }
    }
    renderer.domElement.addEventListener('pointerdown', pointerDown)
    renderer.domElement.addEventListener('pointerup', pointerUp)
    const observer = new ResizeObserver(() => {
      if (!host.clientWidth || !host.clientHeight) return
      renderer.setSize(host.clientWidth, host.clientHeight)
      camera.aspect = host.clientWidth / host.clientHeight
      camera.updateProjectionMatrix()
      dirty = true
    })
    observer.observe(host)
    const draw = () => {
      frame = requestAnimationFrame(draw)
      if (document.hidden) return
      controls.update()
      if (dirty || controls.autoRotate) {
        renderer.render(scene, camera)
        dirty = false
      }
    }
    draw()
    return () => {
      disposed = true
      abort.abort()
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      controlsRef.current = null
      runtime.current = null
      disposeObjects(scene)
      environment.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [manifest])
  return (
    <div className="product-canvas">
      <div
        ref={container}
        className="product-renderer"
        aria-label="CARBENTRA Plug 产品工程参考模型"
      />
      {loading && (
        <div className="product-loading">
          <Loading label={`${phase} · ${Math.round(progress * 100)}%`} />
          <small>按需加载，完成 SHA-256 校验后才显示</small>
        </div>
      )}
      {!!error && (
        <div className="product-loading">
          <ErrorState error={error} />
        </div>
      )}
      <div className="product-view-controls">
        <IconButton
          label="聚焦选中零件"
          disabled={!selected}
          onClick={() => runtime.current?.focus(selected)}
        >
          <Focus size={17} />
        </IconButton>
        <IconButton label="重置产品视角" onClick={() => runtime.current?.reset()}>
          <Maximize2 size={17} />
        </IconButton>
      </div>
      <div className="product-view-note">拖动旋转 · 滚轮缩放 · 点击零件查看参考身份</div>
    </div>
  )
}
