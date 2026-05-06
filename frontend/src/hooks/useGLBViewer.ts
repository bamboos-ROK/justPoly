import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export interface ViewerHandle {
  camera: THREE.PerspectiveCamera
  controls: OrbitControls
  setWireframe: (v: boolean) => void
  setBoundingBox: (v: boolean) => void
}

export function useGLBViewer(canvasRef: React.RefObject<HTMLCanvasElement | null>, glbUrl: string) {
  const handleRef = useRef<ViewerHandle | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [triCount, setTriCount] = useState(0)
  const [fileSizeBytes, setFileSizeBytes] = useState<number | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    setLoaded(false)
    setTriCount(0)
    setFileSizeBytes(null)

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x111827)

    const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 100000)
    camera.position.set(5, 5, 5)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08

    // 기본 조명
    const ambient = new THREE.AmbientLight(0xffffff, 0.7)
    scene.add(ambient)
    const dir = new THREE.DirectionalLight(0xffffff, 1.5)
    dir.position.set(5, 10, 7)
    scene.add(dir)
    const fill = new THREE.DirectionalLight(0x8888ff, 0.3)
    fill.position.set(-5, -2, -5)
    scene.add(fill)

    let bbHelper: THREE.Box3Helper | null = null
    let model: THREE.Object3D | null = null

    const loader = new GLTFLoader()
    loader.load(
      glbUrl,
      (gltf) => {
        model = gltf.scene
        scene.add(model)

        const box = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)

        camera.near = maxDim * 0.0001
        camera.far = maxDim * 100
        camera.position.copy(center).addScaledVector(new THREE.Vector3(1, 1, 1).normalize(), maxDim * 2)
        controls.target.copy(center)
        controls.update()

        let tris = 0
        model.traverse((obj) => {
          if (obj instanceof THREE.Mesh) {
            const geo = obj.geometry
            tris += geo.index ? geo.index.count / 3 : geo.attributes.position.count / 3
          }
        })
        setTriCount(Math.round(tris))
        setLoaded(true)
      },
      (event) => {
        if (event.lengthComputable && event.total > 0) {
          setFileSizeBytes(event.total)
        }
      },
      (err) => console.error('GLTFLoader error', err),
    )

    // Resize
    const ro = new ResizeObserver(() => {
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    })
    ro.observe(canvas)
    // 초기 사이즈 반영
    const w0 = canvas.clientWidth || 400
    const h0 = canvas.clientHeight || 400
    renderer.setSize(w0, h0, false)
    camera.aspect = w0 / h0
    camera.updateProjectionMatrix()

    let rafId: number
    const animate = () => {
      rafId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    handleRef.current = {
      camera,
      controls,
      setWireframe(v: boolean) {
        scene.traverse((obj) => {
          if (obj instanceof THREE.Mesh) {
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
            mats.forEach((m) => { m.wireframe = v })
          }
        })
      },
      setBoundingBox(v: boolean) {
        if (v && !bbHelper && model) {
          const box = new THREE.Box3().setFromObject(model)
          bbHelper = new THREE.Box3Helper(box, new THREE.Color(0x00ff88))
          scene.add(bbHelper)
        } else if (!v && bbHelper) {
          scene.remove(bbHelper)
          bbHelper.dispose()
          bbHelper = null
        }
      },
    }

    return () => {
      cancelAnimationFrame(rafId)
      ro.disconnect()
      controls.dispose()
      renderer.dispose()
      handleRef.current = null
    }
  }, [glbUrl])

  return { handleRef, loaded, triCount, fileSizeBytes }
}
