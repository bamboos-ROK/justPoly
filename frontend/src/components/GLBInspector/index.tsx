import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { ViewerHandle } from '../../hooks/useGLBViewer';
import type { PipelineParams } from '../../types';
import { useSyncCamera } from '../../hooks/useSyncCamera';
import { fmtParams } from '../../utils';
import { ViewerCanvas } from './ViewerCanvas';

interface Props {
  inputUrl: string;
  outputUrl: string;
  open?: boolean;
  title?: string;
  params?: PipelineParams | null;
  onClose?: () => void;
}

export function GLBInspector({
  inputUrl,
  outputUrl,
  open = true,
  title = '결과 비교 보기',
  params,
  onClose
}: Props) {
  const [wireframe, setWireframe] = useState(false);
  const [showBBox, setShowBBox] = useState(false);
  const [syncCam, setSyncCam] = useState(false);

  const beforeHandle = useRef<ViewerHandle | null>(null);
  const afterHandle = useRef<ViewerHandle | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const [beforeControls, setBeforeControls] = useState<ViewerHandle['controls'] | null>(null);
  const [afterControls, setAfterControls] = useState<ViewerHandle['controls'] | null>(null);

  useSyncCamera(syncCam, beforeControls, afterControls);

  useEffect(() => {
    if (!open || !onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const paramsText = fmtParams(params);

  return (
    <div
      ref={backdropRef}
      style={styles.backdrop}
      onClick={(e) => {
        if (e.target === backdropRef.current) onClose?.();
      }}
    >
      <div style={styles.modal}>
        <div style={styles.modalHeader}>
          <span style={styles.modalTitle}>{title}</span>
          {onClose && (
            <button style={styles.closeBtn} onClick={onClose} aria-label="닫기">
              ×
            </button>
          )}
        </div>
        {paramsText && (
          <div style={styles.paramsBar} title={paramsText}>
            params: {paramsText}
          </div>
        )}
        <div style={styles.root}>
          <div style={styles.controls}>
            <Toggle label="Wireframe" value={wireframe} onChange={setWireframe} />
            <Toggle label="Bounding Box" value={showBBox} onChange={setShowBBox} />
            <Toggle label="카메라 동기화" value={syncCam} onChange={setSyncCam} />
          </div>
          <div style={styles.viewers}>
            <ViewerCanvas
              glbUrl={inputUrl}
              label="Before"
              wireframe={wireframe}
              showBBox={showBBox}
              onReady={(h) => {
                beforeHandle.current = h;
                setBeforeControls(h.controls);
              }}
            />
            <div style={styles.divider} />
            <ViewerCanvas
              glbUrl={outputUrl}
              label="After"
              wireframe={wireframe}
              showBBox={showBBox}
              onReady={(h) => {
                afterHandle.current = h;
                setAfterControls(h.controls);
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Toggle({
  label,
  value,
  onChange
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      style={{
        ...styles.toggleBtn,
        background: value ? '#6366f1' : '#1e293b',
        color: value ? '#fff' : '#94a3b8'
      }}
      onClick={() => onChange(!value)}
    >
      {label}
    </button>
  );
}

const styles: Record<string, CSSProperties> = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.75)',
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  modal: {
    position: 'fixed',
    top: '5%',
    left: '5%',
    right: '5%',
    bottom: '5%',
    background: '#0f172a',
    borderRadius: 12,
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 1001,
    overflow: 'hidden'
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 20px',
    borderBottom: '1px solid #334155',
    flexShrink: 0
  },
  modalTitle: { fontSize: 14, fontWeight: 600, color: '#e2e8f0' },
  paramsBar: {
    padding: '6px 20px',
    borderBottom: '1px solid #1e293b',
    color: '#94a3b8',
    fontFamily: 'monospace',
    fontSize: 10,
    lineHeight: 1.4,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flexShrink: 0
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: 18,
    cursor: 'pointer',
    lineHeight: 1,
    padding: '0 4px'
  },
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%'
  },
  controls: {
    display: 'flex',
    gap: 8,
    padding: '10px 16px',
    background: '#0f172a',
    borderBottom: '1px solid #1e293b',
    flexShrink: 0
  },
  toggleBtn: {
    padding: '6px 14px',
    border: '1px solid #334155',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s'
  },
  viewers: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden'
  },
  divider: {
    width: 2,
    background: '#1e293b',
    flexShrink: 0
  }
};
