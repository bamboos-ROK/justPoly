import { useEffect, useRef } from 'react';
import type { ViewerHandle } from '../../hooks/useGLBViewer';
import { useGLBViewer } from '../../hooks/useGLBViewer';
import { fmtSize } from '../../utils';

interface Props {
  glbUrl: string;
  label: string;
  onReady: (handle: ViewerHandle) => void;
  wireframe: boolean;
  showBBox: boolean;
}

export function ViewerCanvas({ glbUrl, label, onReady, wireframe, showBBox }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { handleRef, loaded, triCount, fileSizeBytes } = useGLBViewer(canvasRef, glbUrl);

  useEffect(() => {
    handleRef.current?.setWireframe(wireframe);
  }, [wireframe]);

  useEffect(() => {
    handleRef.current?.setBoundingBox(showBBox);
  }, [showBBox]);

  useEffect(() => {
    if (loaded && handleRef.current) onReady(handleRef.current);
  }, [loaded]);

  return (
    <div style={styles.wrap}>
      <canvas ref={canvasRef} style={styles.canvas} />
      <div style={styles.overlay}>
        <span style={styles.labelBadge}>{label}</span>
        {loaded && <span style={styles.trisBadge}>{triCount.toLocaleString()} tris</span>}
        {fileSizeBytes !== null && <span style={styles.trisBadge}>{fmtSize(fileSizeBytes)}</span>}
      </div>
      {!loaded && (
        <div style={styles.loading}>
          <span>로딩 중...</span>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    background: '#111827'
  },
  canvas: {
    width: '100%',
    height: '100%',
    display: 'block'
  },
  overlay: {
    position: 'absolute',
    top: 12,
    left: 12,
    display: 'flex',
    gap: 8,
    alignItems: 'center'
  },
  labelBadge: {
    background: 'rgba(0,0,0,0.6)',
    color: '#e2e8f0',
    fontSize: 12,
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: 4,
    backdropFilter: 'blur(4px)'
  },
  trisBadge: {
    background: 'rgba(0,0,0,0.5)',
    color: '#94a3b8',
    fontSize: 11,
    padding: '3px 8px',
    borderRadius: 4,
    backdropFilter: 'blur(4px)'
  },
  loading: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#64748b',
    fontSize: 13,
    background: '#111827'
  }
};
