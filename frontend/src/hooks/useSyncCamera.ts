import { useEffect } from 'react'
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export function useSyncCamera(
  enabled: boolean,
  source: OrbitControls | null | undefined,
  target: OrbitControls | null | undefined,
) {
  useEffect(() => {
    if (!enabled || !source || !target) return

    const sync = () => {
      target.object.position.copy(source.object.position)
      target.target.copy(source.target)
      target.update()
    }

    source.addEventListener('change', sync)
    return () => source.removeEventListener('change', sync)
  }, [enabled, source, target])
}
