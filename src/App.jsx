import { Routes, Route } from 'react-router-dom'
import HomePage from './assets/pages/HomePage'
import AuthPage from './assets/pages/AuthPage'
import Overview from './assets/pages/Overview'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/overview" element={<Overview />} />
    </Routes>
  )
}