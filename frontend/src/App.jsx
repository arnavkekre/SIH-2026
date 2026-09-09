import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TopNav from './components/layout/TopNav.jsx'
import { TelemetryProvider } from './providers/TelemetryProvider.jsx'
import Home from './pages/Home.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Diagnostics from './pages/Diagnostics.jsx'
import Missions from './pages/Missions.jsx'
import Analytics from './pages/Analytics.jsx'
import About from './pages/About.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <TelemetryProvider>
        <div className="flex flex-col min-h-screen bg-bg-base">
          <TopNav />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/diagnostics" element={<Diagnostics />} />
              <Route path="/missions" element={<Missions />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </TelemetryProvider>
    </BrowserRouter>
  )
}
