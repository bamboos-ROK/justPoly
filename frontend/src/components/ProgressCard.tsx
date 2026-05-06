import type { Job } from '../types';

interface Props {
  job: Job;
}

const STEP_LABELS: Record<string, string> = {
  extract: '1. Extract (Blender)',
  simplify: '2. Simplify (QEM)',
  bake: '3. Bake & Export (Blender)'
};

const STATUS_COLOR: Record<string, string> = {
  pending: '#475569',
  running: '#22d3ee',
  done: '#22c55e',
  error: '#ef4444'
};

const STATUS_ICON: Record<string, string> = {
  pending: '○',
  running: '◌',
  done: '●',
  error: '✕'
};

export function ProgressCard({ job }: Props) {
  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={{ color: STATUS_COLOR[job.status] }}>
          {job.status === 'running'
            ? '처리 중...'
            : job.status === 'done'
              ? '완료'
              : job.status === 'error'
                ? '오류 발생'
                : '대기 중'}
        </span>
        <span style={styles.filename}>{job.input_filename}</span>
      </div>

      <div style={styles.steps}>
        {job.steps.map((step) => (
          <div key={step.name} style={styles.step}>
            <span style={{ color: STATUS_COLOR[step.status], fontSize: 18 }}>
              {STATUS_ICON[step.status]}
            </span>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  ...styles.stepName,
                  color: step.status === 'pending' ? '#475569' : '#e2e8f0'
                }}
              >
                {STEP_LABELS[step.name] ?? step.name}
              </div>
              {step.log_tail && step.status === 'running' && (
                <pre style={styles.log}>{step.log_tail}</pre>
              )}
            </div>
          </div>
        ))}
      </div>

      {job.error && <pre style={styles.error}>{job.error}</pre>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#1e293b',
    borderRadius: 10,
    padding: 20,
    border: '1px solid #334155'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    fontSize: 14,
    fontWeight: 600
  },
  filename: {
    color: '#94a3b8',
    fontSize: 13,
    maxWidth: 240,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  steps: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12
  },
  step: {
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start'
  },
  stepName: {
    fontSize: 13,
    fontWeight: 500,
    lineHeight: 1.4
  },
  log: {
    marginTop: 6,
    fontSize: 11,
    color: '#64748b',
    background: '#0f172a',
    padding: 8,
    borderRadius: 4,
    overflowX: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    maxHeight: 100,
    overflowY: 'auto'
  },
  error: {
    marginTop: 12,
    fontSize: 11,
    color: '#fca5a5',
    background: '#450a0a',
    padding: 10,
    borderRadius: 6,
    overflowX: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    maxHeight: 160,
    overflowY: 'auto'
  }
};
