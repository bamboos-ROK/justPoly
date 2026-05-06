import { useEffect, useState } from 'react';
import { api } from '../api';
import { GLBInspector } from '../components/GLBInspector';
import type { OutputFile } from '../types';

function fmtSize(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR');
}

export function OutputsPage() {
  const [outputs, setOutputs] = useState<OutputFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<OutputFile | null>(null);

  async function load() {
    try {
      const list = await api.listOutputs();
      setOutputs(list);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>Outputs</h1>
      {loading && <p style={styles.empty}>불러오는 중...</p>}
      {!loading && outputs.length === 0 && <p style={styles.empty}>완료된 결과물이 없습니다.</p>}
      <div style={styles.list}>
        {outputs.map((o) => (
          <div key={o.job_id} style={styles.card}>
            <div style={styles.cardLeft}>
              <div style={styles.filename}>{o.filename}</div>
              <div style={styles.meta}>
                {fmtSize(o.size_bytes)} · {fmtDate(o.created_at)}
              </div>
            </div>
            <button style={styles.btn} onClick={() => setSelectedJob(o)}>
              비교 보기
            </button>
          </div>
        ))}
      </div>

      {selectedJob && (
        <GLBInspector
          open
          title={selectedJob.filename}
          inputUrl={selectedJob.input_url || `/files/staging/${selectedJob.job_id}.glb`}
          outputUrl={selectedJob.output_url || `/files/output/${selectedJob.job_id}.glb`}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32, maxWidth: 800 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 24, color: '#f1f5f9' },
  empty: { color: '#64748b', fontSize: 14 },
  list: { display: 'flex', flexDirection: 'column', gap: 12 },
  card: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    padding: '16px 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  cardLeft: { display: 'flex', flexDirection: 'column', gap: 4 },
  filename: { fontSize: 14, fontWeight: 600, color: '#e2e8f0' },
  meta: { fontSize: 12, color: '#64748b' },
  btn: {
    padding: '8px 16px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    flexShrink: 0
  }
};
