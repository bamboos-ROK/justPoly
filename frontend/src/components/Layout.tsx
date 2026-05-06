import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f172a', color: '#e2e8f0' }}>
      <Sidebar />
      <main style={{ flex: 1, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
