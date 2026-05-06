import type { Job, UploadItem } from '../types'

interface FileJobCardProps {
  item: UploadItem
  job?: Job
  onViewResult: (job_id: string) => void
}

const STATUS_COLOR: Record<string, string> = {
  pending: '#64748b',
  uploading: '#6366f1',
  uploaded: '#22d3ee',
  queued: '#f59e0b',
  running: '#22d3ee',
  done: '#22c55e',
  error: '#ef4444',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '대기',
  uploading: '업로드 중',
  uploaded: '업로드 완료',
  queued: '변환 대기',
  running: '변환 중',
  done: '완료',
  error: '오류',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function FileJobCard({ item, job, onViewResult }: FileJobCardProps) {
  const uploadStatus = item.upload_status
  const convStatus = job?.status
  const displayStatus = convStatus ?? uploadStatus
  const color = STATUS_COLOR[displayStatus] ?? '#64748b'
  const label = STATUS_LABEL[displayStatus] ?? displayStatus

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div style={styles.filename} title={item.filename}>{item.filename}</div>
        <div style={{ ...styles.badge, background: color + '22', color }}>
          {label}
          {convStatus === 'running' && job?.step && ` · ${job.step}`}
        </div>
      </div>
      <div style={styles.size}>{formatBytes(item.size_bytes)}</div>

      {uploadStatus === 'uploading' && (
        <div style={styles.progressWrap}>
          <div style={{ ...styles.progressFill, width: `${item.upload_progress}%` }} />
          <span style={styles.progressText}>{Math.round(item.upload_progress)}%</span>
        </div>
      )}

      {uploadStatus === 'error' && item.error && (
        <div style={styles.errorText}>{item.error}</div>
      )}

      {convStatus === 'error' && job?.error && (
        <div style={styles.errorText}>{job.error}</div>
      )}

      {convStatus === 'done' && item.job_id && (
        <button style={styles.viewBtn} onClick={() => onViewResult(item.job_id!)}>
          결과 비교 보기 →
        </button>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  filename: {
    fontSize: 13,
    fontWeight: 600,
    color: '#e2e8f0',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
  },
  badge: {
    fontSize: 11,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 99,
    flexShrink: 0,
  },
  size: {
    fontSize: 12,
    color: '#64748b',
  },
  progressWrap: {
    position: 'relative',
    height: 20,
    background: '#0f172a',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    position: 'absolute',
    inset: 0,
    right: 'auto',
    background: '#6366f1',
    transition: 'width 0.2s',
  },
  progressText: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 11,
    color: '#e2e8f0',
  },
  errorText: {
    fontSize: 11,
    color: '#ef4444',
    background: 'rgba(239,68,68,0.1)',
    borderRadius: 4,
    padding: '4px 8px',
    maxHeight: 60,
    overflow: 'auto',
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap',
  },
  viewBtn: {
    alignSelf: 'flex-start',
    padding: '6px 14px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  },
}
