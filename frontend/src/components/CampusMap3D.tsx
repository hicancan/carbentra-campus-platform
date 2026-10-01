import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { SpatialManifest } from '../lib/spatial'
import { spatialUrl } from '../lib/spatial'
import { Box, Focus, LocateFixed, Minus, Plus, X } from 'lucide-react'
import { Button, ErrorState, IconButton, Loading } from './ui'
import { detailMeshes, disposeModel } from '../lib/building-detail'
import { campusViewDirection, fitPerspectiveBounds } from '../lib/camera-fit'
import MapAttribution from './MapAttribution'
export default function CampusMap3D({
  manifest,
  allowedIds,
  selected,
  onSelect,
}: {
  manifest: SpatialManifest
  allowedIds: Set<string>
  selected?: string
  onSelect: (id: string) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  const selectRef = useRef(onSelect)
  const selectedRef = useRef(selected)
  const meshes = useRef<THREE.Mesh[]>([])
  const dirtyRef = useRef(true)
  const runtime = useRef<{
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    detail: THREE.Mesh[]
    focus: (objects: THREE.Object3D[]) => void
    reset: () => void
    zoom: (factor: number) => void
  } | null>(null)
  const [detailRequested, setDetailRequested] = useState<string | null>(null)
  const [detailAttempt, setDetailAttempt] = useState(0)
  const [detailStatus, setDetailStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [detailError, setDetailError] = useState<unknown>(null)
  const selectedEntry = manifest.buildings.find(
    (building) => building.building_id === selected && allowedIds.has(building.building_id),
  )
  useEffect(() => {
    setDetailRequested(null)
    setDetailStatus('idle')
    setDetailError(null)
  }, [selected])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [hover, setHover] = useState('')
  const [contextStatus, setContextStatus] = useState<'none' | 'loading' | 'ready' | 'unavailable'>(
    'none',
  )
  selectRef.current = onSelect
  selectedRef.current = selected
  useEffect(() => {
    for (const mesh of meshes.current) {
      const mat = mesh.material as THREE.MeshStandardMaterial
      mat.color.set(mesh.userData.buildingId === selected ? '#267d6a' : '#dadfcb')
    }
    dirtyRef.current = true
  }, [selected])
  useEffect(() => {
    const current = runtime.current
    if (
      !current ||
      loading ||
      !selectedEntry?.detail_mesh_url ||
      detailRequested !== selectedEntry.building_id
    ) {
      setDetailStatus('idle')
      setDetailError(null)
      return
    }
    const abort = new AbortController()
    let cancelled = false
    let model: THREE.Group | null = null
    const base = meshes.current.filter(
      (mesh) => mesh.userData.buildingId === selectedEntry.building_id,
    )
    setDetailStatus('loading')
    setDetailError(null)
    const load = async () => {
      const expected = selectedEntry.detail_bytes
      if (
        expected != null &&
        (!Number.isSafeInteger(expected) || expected <= 0 || expected > 16 * 1024 * 1024)
      )
        throw new Error('外观产物大小超出单楼栋加载范围')
      const response = await fetch(
        spatialUrl(
          selectedEntry.detail_mesh_url!,
          selectedEntry.detail_mesh_sha256 || manifest.version,
        ),
        {
          signal: abort.signal,
          credentials: 'include',
        },
      )
      if (!response.ok)
        throw new Error(`楼栋外观暂时不可用（HTTP ${response.status}），基础模型仍可使用`)
      const declared = Number(response.headers.get('Content-Length') || 0)
      if (declared > 16 * 1024 * 1024) throw new Error('楼栋外观超出允许的产物大小')
      const buffer = await response.arrayBuffer()
      if (
        buffer.byteLength > 16 * 1024 * 1024 ||
        (expected != null && expected !== buffer.byteLength)
      )
        throw new Error('楼栋外观大小与发布清单不一致')
      if (cancelled) return
      if (selectedEntry.detail_mesh_sha256) {
        if (!/^[a-f0-9]{64}$/i.test(selectedEntry.detail_mesh_sha256) || !globalThis.crypto?.subtle)
          throw new Error('外观完整性校验需要有效清单及 HTTPS 或本机安全环境')
        const digest = await crypto.subtle.digest('SHA-256', buffer)
        const actual = [...new Uint8Array(digest)]
          .map((value) => value.toString(16).padStart(2, '0'))
          .join('')
        if (actual !== selectedEntry.detail_mesh_sha256.toLowerCase())
          throw new Error('外观模型 SHA-256 校验失败，已保留基础模型')
      }
      if (cancelled) return
      const manager = new THREE.LoadingManager()
      manager.setURLModifier((url) => {
        if (!url.startsWith('blob:') && !url.startsWith('data:'))
          throw new Error('外观模型不能读取外部资源')
        return url
      })
      const gltf = await new GLTFLoader(manager).parseAsync(buffer, '')
      if (cancelled) {
        disposeModel(gltf.scene)
        return
      }
      model = gltf.scene
      const detailed = detailMeshes(model, selectedEntry.asset_id, selectedEntry.building_id)
      detailed.forEach((mesh) => {
        mesh.userData.name = selectedEntry.name
      })
      // Published transforms already use campus E/up/-N; do not place the model twice.
      current.scene.add(model)
      base.forEach((mesh) => {
        mesh.visible = false
      })
      current.detail = detailed
      current.focus([model])
      dirtyRef.current = true
      setDetailStatus('ready')
    }
    void load().catch((error) => {
      if (model) {
        current.scene.remove(model)
        disposeModel(model)
        model = null
      }
      base.forEach((mesh) => {
        mesh.visible = true
      })
      current.detail = []
      dirtyRef.current = true
      if (!cancelled) {
        setDetailError(error)
        setDetailStatus('error')
      }
    })
    return () => {
      cancelled = true
      abort.abort()
      current.detail = []
      if (model) {
        current.scene.remove(model)
        disposeModel(model)
      }
      base.forEach((mesh) => {
        mesh.visible = true
      })
      dirtyRef.current = true
    }
  }, [detailRequested, detailAttempt, selectedEntry, loading, manifest.version])
  useEffect(() => {
    if (!ref.current) return
    setLoading(true)
    setError(null)
    setContextStatus(manifest.context_mesh_url ? 'loading' : 'none')
    dirtyRef.current = true
    let disposed = false
    let frame = 0
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    } catch {
      setError(new Error('当前浏览器无法启用 WebGL。请切换二维地图继续浏览全部楼栋。'))
      setLoading(false)
      return
    }
    const container = ref.current
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#e9eee5')
    scene.fog = new THREE.Fog('#e9eee5', 2500, 7500)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 0.95
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.appendChild(renderer.domElement)
    const camera = new THREE.PerspectiveCamera(
      38,
      container.clientWidth / container.clientHeight,
      1,
      15000,
    )
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.addEventListener('change', () => {
      dirtyRef.current = true
    })
    controls.maxPolarAngle = Math.PI / 2.04
    controls.minDistance = 10
    controls.maxDistance = 6000
    let framedBounds: THREE.Box3 | null = null
    let campusBounds: THREE.Box3 | null = null
    const fit = (box: THREE.Box3, direction = camera.position.clone().sub(controls.target)) => {
      framedBounds = box.clone()
      controls.target.copy(fitPerspectiveBounds(camera, box, direction))
      if (scene.fog instanceof THREE.Fog) {
        const span = box.getSize(new THREE.Vector3()).length()
        scene.fog.near = camera.position.distanceTo(controls.target) + span * 0.6
        scene.fog.far = scene.fog.near + span * 3
      }
      controls.update()
      dirtyRef.current = true
    }
    runtime.current = {
      scene,
      camera,
      controls,
      detail: [],
      reset: () => {
        if (campusBounds) fit(campusBounds, campusViewDirection(camera.aspect))
      },
      zoom: (factor) => {
        camera.position.sub(controls.target).multiplyScalar(factor).add(controls.target)
        controls.update()
        dirtyRef.current = true
      },
      focus: (objects) => {
        const box = new THREE.Box3()
        objects.forEach((object) => box.expandByObject(object))
        if (!box.isEmpty()) fit(box)
      },
    }
    scene.add(new THREE.HemisphereLight('#f4f7ff', '#67725f', 1.1))
    const sun = new THREE.DirectionalLight('#fff4df', 2)
    sun.position.set(-500, 1000, 300)
    sun.castShadow = true
    sun.shadow.mapSize.set(2048, 2048)
    Object.assign(sun.shadow.camera, {
      left: -1500,
      right: 1500,
      top: 1500,
      bottom: -1500,
      far: 4000,
    })
    sun.shadow.bias = -0.001
    scene.add(sun)
    const bounds = new THREE.Box3()
    const lookup = new Map(manifest.buildings.map((b) => [b.node_name, b]))
    const localMeshes: THREE.Mesh[] = []
    const loader = new GLTFLoader()
    loader.setWithCredentials(true)
    loader.load(
      spatialUrl(manifest.campus_mesh_url, manifest.version),
      (gltf) => {
        if (disposed) {
          gltf.scene.traverse((o) => {
            if (o instanceof THREE.Mesh) o.geometry.dispose()
          })
          return
        }
        gltf.scene.traverse((object) => {
          if (!(object instanceof THREE.Mesh)) return
          let node: THREE.Object3D | null = object
          let building
          while (node && !building) {
            building = lookup.get(node.name)
            node = node.parent
          }
          if (!building || !allowedIds.has(building.building_id)) {
            object.visible = false
            return
          }
          object.userData.buildingId = building.building_id
          object.userData.name = building.name
          ;(Array.isArray(object.material) ? object.material : [object.material]).forEach(
            (material) => material.dispose(),
          )
          object.material = new THREE.MeshStandardMaterial({
            color: building.building_id === selectedRef.current ? '#267d6a' : '#dadfcb',
            roughness: 0.8,
            metalness: 0,
          })
          object.castShadow = true
          object.receiveShadow = true
          bounds.expandByObject(object)
          localMeshes.push(object)
        })
        scene.add(gltf.scene)
        meshes.current = localMeshes
        if (bounds.isEmpty()) {
          setError(new Error('当前校区暂无已发布的三维几何，请使用空间列表。'))
          setLoading(false)
          return
        }
        const center = bounds.getCenter(new THREE.Vector3())
        const size = bounds.getSize(new THREE.Vector3())
        const span = Math.max(size.x, size.z)
        campusBounds = bounds.clone()
        fit(bounds, campusViewDirection(camera.aspect))
        const ground = new THREE.Mesh(
          new THREE.PlaneGeometry(span * 10, span * 10),
          new THREE.MeshStandardMaterial({ color: '#e7eddf', roughness: 1 }),
        )
        ground.rotation.x = -Math.PI / 2
        ground.position.set(center.x, -0.2, center.z)
        ground.receiveShadow = true
        scene.add(ground)
        const grid = new THREE.GridHelper(span * 3, 50, '#c7d2be', '#d8dfd1')
        grid.position.set(center.x, 0.05, center.z)
        ;(grid.material as THREE.Material).transparent = true
        ;(grid.material as THREE.Material).opacity = 0.35
        scene.add(grid)
        if (manifest.context_mesh_url) {
          loader.load(
            spatialUrl(manifest.context_mesh_url, manifest.version),
            (context) => {
              if (disposed) {
                context.scene.traverse((object) => {
                  if (object instanceof THREE.Mesh) {
                    object.geometry.dispose()
                    ;(Array.isArray(object.material) ? object.material : [object.material]).forEach(
                      (material) => material.dispose(),
                    )
                  }
                })
                return
              }
              // Keep authored PBR materials and preserve the distinct non-pickable context namespace.
              context.scene.traverse((object) => {
                if (object instanceof THREE.Mesh) {
                  object.receiveShadow = true
                  object.castShadow = false
                }
              })
              scene.add(context.scene)
              dirtyRef.current = true
              grid.visible = false
              setContextStatus('ready')
            },
            undefined,
            () => {
              if (!disposed) setContextStatus('unavailable')
            },
          )
        }
        dirtyRef.current = true
        setLoading(false)
      },
      undefined,
      () => {
        if (!disposed) {
          setError(new Error('三维产物加载失败，请切换二维视图或稍后重试。'))
          setLoading(false)
        }
      },
    )
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    let down = { x: 0, y: 0 }
    const pick = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(pointer, camera)
      return raycaster.intersectObjects(
        [...localMeshes.filter((mesh) => mesh.visible), ...(runtime.current?.detail || [])],
        false,
      )[0]?.object
    }
    const move = (event: PointerEvent) => {
      const object = pick(event)
      setHover(object?.userData.name || '')
      renderer.domElement.style.cursor = object ? 'pointer' : 'grab'
    }
    const pointerDown = (event: PointerEvent) => {
      down = { x: event.clientX, y: event.clientY }
    }
    const up = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - down.x, event.clientY - down.y) > 5) return
      const object = pick(event)
      if (object?.userData.buildingId) selectRef.current(object.userData.buildingId)
    }
    renderer.domElement.addEventListener('pointermove', move)
    renderer.domElement.addEventListener('pointerdown', pointerDown)
    renderer.domElement.addEventListener('pointerup', up)
    const observer = new ResizeObserver(() => {
      if (!container.clientWidth || !container.clientHeight) return
      renderer.setSize(container.clientWidth, container.clientHeight)
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      if (framedBounds) fit(framedBounds)
      dirtyRef.current = true
    })
    observer.observe(container)
    const draw = () => {
      frame = requestAnimationFrame(draw)
      controls.update()
      if (dirtyRef.current) {
        renderer.render(scene, camera)
        dirtyRef.current = false
      }
    }
    draw()
    return () => {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh || o instanceof THREE.LineSegments) {
          o.geometry.dispose()
          ;(Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose())
        }
      })
      runtime.current = null
      renderer.dispose()
      renderer.domElement.remove()
      meshes.current = []
    }
  }, [manifest, allowedIds])
  return (
    <div className="campus-map three-map">
      <div className="three-container" ref={ref} aria-label="可旋转的校园三维地图" />
      {loading && (
        <div className="map-overlay-state">
          <Loading label="正在加载轻量校园模型…" />
        </div>
      )}
      {!!error && (
        <div className="map-overlay-state">
          <ErrorState error={error} />
        </div>
      )}
      {selectedEntry && !loading && !error && (
        <div className="map-detail-toolbar">
          <div>
            <strong>{selectedEntry.name}</strong>
            <span>
              {detailStatus === 'ready' ? '外观细节 · 源作者推导' : '基础 LOD1 · 推导高度'}
            </span>
          </div>
          <Button
            className="button-small"
            onClick={() =>
              runtime.current?.focus(
                runtime.current.detail.length
                  ? runtime.current.detail
                  : meshes.current.filter(
                      (mesh) => mesh.userData.buildingId === selectedEntry.building_id,
                    ),
              )
            }
          >
            <Focus size={13} />
            聚焦楼栋
          </Button>
          {selectedEntry.detail_mesh_url &&
            (detailRequested === selectedEntry.building_id && detailStatus !== 'error' ? (
              <Button className="button-small" onClick={() => setDetailRequested(null)}>
                <X size={13} />
                {detailStatus === 'loading' ? '取消读取' : '卸载外观细节'}
              </Button>
            ) : (
              <Button
                className="button-small"
                onClick={() => {
                  setDetailRequested(selectedEntry.building_id)
                  setDetailAttempt((value) => value + 1)
                  setDetailStatus('idle')
                }}
              >
                <Box size={13} />
                {detailStatus === 'error' ? '重试外观细节' : '读取外观细节'}
                {selectedEntry.detail_bytes
                  ? ` · ${(selectedEntry.detail_bytes / 1024 / 1024).toFixed(1)} MiB`
                  : ''}
              </Button>
            ))}
          {detailStatus === 'loading' && <span role="status">仅加载这一栋的外观参考…</span>}
          {detailStatus === 'ready' && <span>外观参考 · 原始材质</span>}
          {!!detailError && detailRequested === selectedEntry.building_id && (
            <ErrorState error={detailError} compact />
          )}
        </div>
      )}
      {hover && (
        <div className="map-hover">
          <strong>{hover}</strong>
          <span>点击查看楼栋</span>
        </div>
      )}
      {contextStatus !== 'none' && (
        <div className="map-context-status">
          {contextStatus === 'ready'
            ? '道路 · 绿地 · 水系：源参考场景'
            : contextStatus === 'loading'
              ? '正在读取背景场景…'
              : '背景参考未加载，楼栋仍可使用'}
        </div>
      )}
      {!loading && !error && (
        <div className="map-controls">
          <IconButton label="放大三维视图" onClick={() => runtime.current?.zoom(0.8)}>
            <Plus size={16} />
          </IconButton>
          <IconButton label="缩小三维视图" onClick={() => runtime.current?.zoom(1.25)}>
            <Minus size={16} />
          </IconButton>
          <IconButton label="重置校园视角" onClick={() => runtime.current?.reset()}>
            <LocateFixed size={16} />
          </IconButton>
        </div>
      )}
      <div className="map-instructions">左键旋转 · 右键平移 · 滚轮缩放</div>
      <MapAttribution />
    </div>
  )
}
