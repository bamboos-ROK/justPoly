import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { GLBInspector } from '../components/GLBInspector'
import { ProgressCard } from '../components/ProgressCard'
import { UploadZone } from '../components/UploadZone'
import { useStore } from '../store'
import type { PipelineParams } from '../types'

export function OnProgressPage() {
  const { activeJob, setActiveJob, updateJob, setPollingId } = useStore()

  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<{ job_id: string; filename: string } | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [params, setParams] = useState<Partial<PipelineParams>>({
    tris_ratio: 0.1,
    texture_ratio: 0.5,
    skip_high_poly_cleanup: false,
    skip_cage: false,
  })
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  function startPolling(job_id: string) {
    if (pollingRef.current) clearInterval(pollingRef.current)
    const id = setInterval(async () => {
      try {
        const job = await api.getJob(job_id)
        updateJob(job)
        if (job.status === 'done' || job.status === 'error') {
          clearInterval(id)
          pollingRef.current = null
        }
      } catch (_) { /* ignore */ }
    }, 2000)
    pollingRef.current = id
    setPollingId(id)
  }

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  async function handleFile(file: File) {
    setBusy(true)
    setUploadPct(0)
    setActiveJob(null)
    setUploadedFile(null)
    try {
      const { job_id } = await api.uploadGLB(file, setUploadPct)
      setUploadedFile({ job_id, filename: file.name })
    } catch (e) {
      alert(`오류: ${(e as Error).message}`)
    } finally {
      setBusy(false)
      setUploadPct(null)
    }
  }

  async function handleStartPipeline() {
    if (!uploadedFile) return
    setBusy(true)
    try {
      const job = await api.startPipeline(uploadedFile.job_id, params)
      setActiveJob({ ...job, input_filename: uploadedFile.filename })
      startPolling(uploadedFile.job_id)
    } catch (e) {
      alert(`오류: ${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  const isRunning = activeJob?.status === 'running'
  const canStartPipeline = Boolean(uploadedFile) && !busy && !isRunning

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>On Progress</h1>

      <UploadZone onFile={handleFile} disabled={busy || isRunning} />

      {uploadPct !== null && (
        <div style={styles.uploadBar}>
          <div style={{ ...styles.uploadFill, width: `${uploadPct}%` }} />
          <span style={styles.uploadText}>{Math.round(uploadPct)}% 업로드 중...</span>
        </div>
      )}

      {/* 파라미터 설정 */}
      {!isRunning && (
        <div style={styles.paramBox}>
          <label style={styles.label}>
            삼각형 비율 ({Math.round((params.tris_ratio ?? 0.1) * 100)}%)
            <input
              type="range" min={0.01} max={0.5} step={0.01}
              value={params.tris_ratio ?? 0.1}
              onChange={(e) => setParams((p) => ({ ...p, tris_ratio: parseFloat(e.target.value) }))}
              style={styles.range}
            />
          </label>
          <label style={styles.label}>
            텍스처 비율 ({Math.round((params.texture_ratio ?? 0.5) * 100)}%)
            <input
              type="range" min={0.1} max={1.0} step={0.05}
              value={params.texture_ratio ?? 0.5}
              onChange={(e) => setParams((p) => ({ ...p, texture_ratio: parseFloat(e.target.value) }))}
              style={styles.range}
            />
          </label>
          <div style={styles.checkRow}>
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={params.skip_high_poly_cleanup ?? false}
                onChange={(e) => setParams((p) => ({ ...p, skip_high_poly_cleanup: e.target.checked }))}
              />
              High Poly Cleanup 스킵
            </label>
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={params.skip_cage ?? false}
                onChange={(e) => setParams((p) => ({ ...p, skip_cage: e.target.checked }))}
              />
              Cage Baking 스킵
            </label>
          </div>
        </div>
      )}

      {uploadedFile && !activeJob && (
        <div style={styles.readyBox}>
          <div>
            <div style={styles.readyTitle}>업로드 완료</div>
            <div style={styles.readyFilename}>{uploadedFile.filename}</div>
          </div>
          <button
            style={{
              ...styles.startBtn,
              ...(canStartPipeline ? {} : styles.disabledBtn),
            }}
            onClick={handleStartPipeline}
            disabled={!canStartPipeline}
          >
            {busy ? '준비 중...' : '경량화 시작'}
          </button>
        </div>
      )}

      {activeJob && (
        <div style={{ marginTop: 24 }}>
          <ProgressCard job={activeJob} />
          {activeJob.status === 'done' && (
            <button
              style={styles.viewBtn}
              onClick={() => setInspectorOpen(true)}
            >
              결과 비교 보기 →
            </button>
          )}
        </div>
      )}

      {activeJob?.status === 'done' && (
        <GLBInspector
          open={inspectorOpen}
          title={activeJob.input_filename}
          inputUrl={`/files/staging/${activeJob.job_id}.glb`}
          outputUrl={activeJob.output_url || `/files/output/${activeJob.job_id}.glb`}
          onClose={() => setInspectorOpen(false)}
        />
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32, maxWidth: 680 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 24, color: '#f1f5f9' },
  uploadBar: {
    position: 'relative',
    height: 32,
    background: '#1e293b',
    borderRadius: 6,
    marginTop: 12,
    overflow: 'hidden',
  },
  uploadFill: {
    position: 'absolute',
    inset: 0,
    right: 'auto',
    background: '#6366f1',
    transition: 'width 0.2s',
  },
  uploadText: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 12,
    color: '#e2e8f0',
  },
  paramBox: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    padding: 20,
    marginTop: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    fontSize: 13,
    color: '#94a3b8',
    fontWeight: 500,
  },
  range: { accentColor: '#6366f1', cursor: 'pointer' },
  checkRow: { display: 'flex', gap: 24 },
  checkLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#94a3b8',
    cursor: 'pointer',
  },
  readyBox: {
    marginTop: 20,
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    padding: '16px 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  readyTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#e2e8f0',
    marginBottom: 4,
  },
  readyFilename: {
    fontSize: 12,
    color: '#94a3b8',
    maxWidth: 360,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  startBtn: {
    padding: '10px 18px',
    background: '#22c55e',
    color: '#082f1a',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 700,
    cursor: 'pointer',
    flexShrink: 0,
  },
  disabledBtn: {
    opacity: 0.55,
    cursor: 'not-allowed',
  },
  viewBtn: {
    marginTop: 16,
    padding: '10px 20px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
}
