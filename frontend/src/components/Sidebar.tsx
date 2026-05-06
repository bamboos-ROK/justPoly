import { NavLink } from 'react-router-dom'
import { useStore } from '../store'

export function Sidebar() {
  const jobsById = useStore((s) => s.jobsById)
  const hasActive = Object.values(jobsById).some(
    (j) => j.status === 'running' || j.status === 'queued'
  )

  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>GLB Optimizer</div>
      <nav style={styles.nav}>
        <NavLink to="/progress" style={navStyle}>
          <span style={styles.icon}>⚙</span>
          On Progress
          {hasActive && <span style={styles.badge} />}
        </NavLink>
        <NavLink to="/outputs" style={navStyle}>
          <span style={styles.icon}>◎</span>
          Outputs
        </NavLink>
      </nav>
    </aside>
  )
}

function navStyle({ isActive }: { isActive: boolean }): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 16px',
    borderRadius: 6,
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
    color: isActive ? '#e2e8f0' : '#94a3b8',
    background: isActive ? 'rgba(99,102,241,0.2)' : 'transparent',
    position: 'relative',
  }
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: 220,
    minHeight: '100vh',
    background: '#0f172a',
    borderRight: '1px solid #1e293b',
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 12px',
    flexShrink: 0,
  },
  logo: {
    color: '#e2e8f0',
    fontSize: 16,
    fontWeight: 700,
    padding: '0 8px',
    marginBottom: 24,
    letterSpacing: '-0.02em',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  icon: {
    fontSize: 16,
  },
  badge: {
    position: 'absolute',
    right: 12,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#22d3ee',
    animation: 'pulse 1.5s infinite',
  },
}
