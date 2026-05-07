import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { FileJobCard } from '../components/FileJobCard';
import { GLBInspector } from '../components/GLBInspector';
import { UploadZone } from '../components/UploadZone';
import { useStore } from '../store';
import type { PipelineParams, UploadItem } from '../types';

const MAX_FILES = 10;
const MAX_FILE_SIZE = 300 * 1024 * 1024; // 300MB
const MAX_CONCURRENT_UPLOADS = 3;

export function OnProgressPage() {
  const {
    uploadItems,
    setUploadItems,
    updateUploadItem,
    jobsById,
    mergeJobs,
    selectedJobId,
    setSelectedJobId,
    setPollingId
  } = useStore();

  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [startingAll, setStartingAll] = useState(false);
  const [params, setParams] = useState<Partial<PipelineParams>>({
    tris_ratio: 0.1,
    texture_ratio: 0.5,
    skip_high_poly_cleanup: false,
    skip_cage: false,
    skip_normal_bake: false
  });

  const uploadQueueRef = useRef<string[]>([]);
  const runningCountRef = useRef(0);
  // uploadItems는 store에 있지만 드레인 함수에서 최신 값 참조가 필요
  const uploadItemsRef = useRef<UploadItem[]>(uploadItems);
  useEffect(() => {
    uploadItemsRef.current = uploadItems;
  }, [uploadItems]);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 폴링 시작
  function startPolling() {
    if (pollingRef.current) return;
    const id = setInterval(async () => {
      try {
        const jobs = await api.listJobs();
        mergeJobs(jobs);
      } catch (_) {
        /* ignore */
      }
    }, 2000);
    pollingRef.current = id;
    setPollingId(id);
  }

  // 폴링 중지 조건 확인
  useEffect(() => {
    const itemsWithJob = uploadItems.filter((i) => i.job_id);
    if (itemsWithJob.length === 0) return;
    const allDone = itemsWithJob.every((i) => {
      const job = i.job_id ? jobsById[i.job_id] : undefined;
      return job?.status === 'done' || job?.status === 'error';
    });
    if (allDone && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
      setPollingId(null);
    }
  }, [jobsById, uploadItems, setPollingId]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const uploadOne = useCallback(
    (local_id: string) => {
      const item = uploadItemsRef.current.find((i) => i.local_id === local_id);
      if (!item) {
        runningCountRef.current--;
        drainQueue();
        return;
      }

      updateUploadItem(local_id, { upload_status: 'uploading', upload_progress: 0 });

      api
        .uploadGLB(item.file, (pct) => {
          updateUploadItem(local_id, { upload_progress: pct });
        })
        .then(({ job_id, input_url }) => {
          updateUploadItem(local_id, {
            upload_status: 'uploaded',
            upload_progress: 100,
            job_id,
            input_url
          });
          startPolling();
        })
        .catch((e) => {
          updateUploadItem(local_id, { upload_status: 'error', error: (e as Error).message });
        })
        .finally(() => {
          runningCountRef.current--;
          drainQueue();
        });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [updateUploadItem]
  );

  function drainQueue() {
    while (runningCountRef.current < MAX_CONCURRENT_UPLOADS && uploadQueueRef.current.length > 0) {
      const local_id = uploadQueueRef.current.shift()!;
      runningCountRef.current++;
      uploadOne(local_id);
    }
  }

  function handleFiles(files: File[]) {
    const glbFiles = files.filter((f) => f.name.toLowerCase().endsWith('.glb'));
    const validFiles = glbFiles.filter((f) => f.size <= MAX_FILE_SIZE);
    const oversized = glbFiles.length - validFiles.length;
    const nonGlb = files.length - glbFiles.length;

    const messages: string[] = [];
    if (nonGlb > 0) messages.push(`${nonGlb}개 파일은 .glb 형식이 아니어서 제외되었습니다.`);
    if (oversized > 0) messages.push(`${oversized}개 파일이 300MB를 초과하여 제외되었습니다.`);

    const currentCount = uploadItemsRef.current.length;
    const available = MAX_FILES - currentCount;
    if (available <= 0) {
      alert(`이미 최대 ${MAX_FILES}개 파일이 등록되어 있습니다.`);
      return;
    }

    const toAdd = validFiles.slice(0, available);
    if (validFiles.length > available) {
      messages.push(
        `${validFiles.length - available}개 파일이 최대 ${MAX_FILES}개 제한으로 제외되었습니다.`
      );
    }

    if (messages.length > 0) alert(messages.join('\n'));
    if (toAdd.length === 0) return;

    const newItems: UploadItem[] = toAdd.map((file) => ({
      local_id: crypto.randomUUID(),
      file,
      filename: file.name,
      size_bytes: file.size,
      upload_status: 'pending',
      upload_progress: 0
    }));

    const fullItems = [...uploadItemsRef.current, ...newItems];
    uploadItemsRef.current = fullItems;
    setUploadItems(fullItems);
    for (const item of newItems) uploadQueueRef.current.push(item.local_id);
    drainQueue();
  }

  async function handleStartAll() {
    const toStart = uploadItems.filter((i) => {
      if (!i.job_id) return false;
      const job = jobsById[i.job_id];
      return job?.status === 'uploaded';
    });
    if (toStart.length === 0) return;
    setStartingAll(true);
    try {
      await Promise.all(toStart.map((i) => api.startPipeline(i.job_id!, params)));
      const jobs = await api.listJobs();
      mergeJobs(jobs);
    } catch (e) {
      alert(`오류: ${(e as Error).message}`);
    } finally {
      setStartingAll(false);
    }
  }

  function handleClearAll() {
    const anyUploading = uploadItems.some((i) => i.upload_status === 'uploading');
    if (anyUploading) return;
    uploadQueueRef.current = [];
    setUploadItems([]);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
      setPollingId(null);
    }
  }

  const readyToStartCount = uploadItems.filter((i) => {
    if (!i.job_id) return false;
    return jobsById[i.job_id]?.status === 'uploaded';
  }).length;

  const anyUploading = uploadItems.some((i) => i.upload_status === 'uploading');
  const isRunning = Object.values(jobsById).some((j) => j.status === 'running');

  const selectedJob = selectedJobId ? jobsById[selectedJobId] : null;

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>On Progress</h1>

      <UploadZone onFiles={handleFiles} disabled={anyUploading || isRunning} />

      {/* 파라미터 설정 */}
      {!isRunning && (
        <div style={styles.paramBox}>
          <label style={styles.label}>
            삼각형 비율 ({Math.round((params.tris_ratio ?? 0.1) * 100)}%)
            <input
              type="range"
              min={0.01}
              max={0.5}
              step={0.01}
              value={params.tris_ratio ?? 0.1}
              onChange={(e) => setParams((p) => ({ ...p, tris_ratio: parseFloat(e.target.value) }))}
              style={styles.range}
            />
          </label>
          <label style={styles.label}>
            텍스처 비율 ({Math.round((params.texture_ratio ?? 0.5) * 100)}%)
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.05}
              value={params.texture_ratio ?? 0.5}
              onChange={(e) =>
                setParams((p) => ({ ...p, texture_ratio: parseFloat(e.target.value) }))
              }
              style={styles.range}
            />
          </label>
          <div style={styles.checkRow}>
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={params.skip_high_poly_cleanup ?? false}
                onChange={(e) =>
                  setParams((p) => ({ ...p, skip_high_poly_cleanup: e.target.checked }))
                }
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
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={params.skip_normal_bake ?? false}
                onChange={(e) => setParams((p) => ({ ...p, skip_normal_bake: e.target.checked }))}
              />
              Normal Map 스킵
            </label>
          </div>
        </div>
      )}

      {/* 액션 버튼 영역 */}
      {uploadItems.length > 0 && (
        <div style={styles.actionRow}>
          <button
            style={{
              ...styles.startBtn,
              ...(readyToStartCount === 0 || startingAll ? styles.disabledBtn : {})
            }}
            onClick={handleStartAll}
            disabled={readyToStartCount === 0 || startingAll}
          >
            {startingAll ? '등록 중...' : `경량화 시작 (${readyToStartCount}개)`}
          </button>
          <button
            style={{
              ...styles.clearBtn,
              ...(anyUploading ? styles.disabledBtn : {})
            }}
            onClick={handleClearAll}
            disabled={anyUploading}
          >
            모두 지우기
          </button>
        </div>
      )}

      {/* 파일 카드 리스트 */}
      {uploadItems.length > 0 && (
        <div style={styles.cardList}>
          {uploadItems.map((item) => {
            const job = item.job_id ? jobsById[item.job_id] : undefined;
            return (
              <FileJobCard
                key={item.local_id}
                item={item}
                job={job}
                onViewResult={(job_id) => {
                  setSelectedJobId(job_id);
                  setInspectorOpen(true);
                }}
              />
            );
          })}
        </div>
      )}

      {selectedJob?.status === 'done' && (
        <GLBInspector
          open={inspectorOpen}
          title={selectedJob.input_filename}
          inputUrl={`/files/staging/${selectedJob.job_id}.glb`}
          outputUrl={selectedJob.output_url ?? `/files/output/${selectedJob.job_id}.glb`}
          params={selectedJob.params}
          onClose={() => {
            setInspectorOpen(false);
            setSelectedJobId(null);
          }}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32, maxWidth: 720 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 24, color: '#f1f5f9' },
  paramBox: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 10,
    padding: 20,
    marginTop: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 16
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    fontSize: 13,
    color: '#94a3b8',
    fontWeight: 500
  },
  range: { accentColor: '#6366f1', cursor: 'pointer' },
  checkRow: { display: 'flex', gap: 24 },
  checkLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#94a3b8',
    cursor: 'pointer'
  },
  actionRow: {
    marginTop: 20,
    display: 'flex',
    gap: 12,
    alignItems: 'center'
  },
  startBtn: {
    padding: '10px 18px',
    background: '#22c55e',
    color: '#082f1a',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 700,
    cursor: 'pointer'
  },
  clearBtn: {
    padding: '10px 18px',
    background: '#334155',
    color: '#94a3b8',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer'
  },
  disabledBtn: {
    opacity: 0.45,
    cursor: 'not-allowed'
  },
  cardList: {
    marginTop: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 10
  }
};
