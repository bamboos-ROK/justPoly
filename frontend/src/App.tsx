import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { OnProgressPage } from './pages/OnProgressPage'
import { OutputsPage } from './pages/OutputsPage'

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/progress" replace />} />
          <Route path="progress" element={<OnProgressPage />} />
          <Route path="outputs" element={<OutputsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/progress" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
