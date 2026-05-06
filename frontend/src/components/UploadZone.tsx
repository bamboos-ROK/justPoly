import { useRef, useState } from 'react'

interface Props {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export function UploadZone({ onFiles, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) onFiles(files)
  }

  return (
    <div
      style={{
        ...styles.zone,
        borderColor: dragging ? '#6366f1' : '#334155',
        background: dragging ? 'rgba(99,102,241,0.08)' : '#1e293b',
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".glb"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length > 0) onFiles(files)
          e.target.value = ''
        }}
        disabled={disabled}
      />
      <div style={styles.icon}>↑</div>
      <div style={styles.text}>GLB 파일을 드래그하거나 클릭하여 선택</div>
      <div style={styles.sub}>최대 10개, 파일당 300MB, .glb 형식</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  zone: {
    border: '2px dashed',
    borderRadius: 12,
    padding: '48px 32px',
    textAlign: 'center',
    transition: 'all 0.2s',
    userSelect: 'none',
  },
  icon: {
    fontSize: 36,
    marginBottom: 12,
    color: '#6366f1',
  },
  text: {
    fontSize: 15,
    fontWeight: 500,
    color: '#e2e8f0',
    marginBottom: 6,
  },
  sub: {
    fontSize: 13,
    color: '#64748b',
  },
}
