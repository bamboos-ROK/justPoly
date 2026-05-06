import { useRef, useState } from 'react'

interface Props {
  onFile: (file: File) => void
  disabled?: boolean
}

export function UploadZone({ onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
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
        style={{ display: 'none' }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
        disabled={disabled}
      />
      <div style={styles.icon}>↑</div>
      <div style={styles.text}>GLB 파일을 드래그하거나 클릭하여 선택</div>
      <div style={styles.sub}>최대 100MB+, .glb 형식</div>
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
