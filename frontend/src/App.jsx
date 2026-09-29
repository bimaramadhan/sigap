import { useState } from 'react'
import { Bell, Map, BarChart2, MessageSquare } from 'lucide-react'
import clsx from 'clsx'

import Header            from './components/Header.jsx'
import WeatherBar        from './components/WeatherBar.jsx'
import MapView           from './components/MapView.jsx'
import AlertPanel        from './components/AlertPanel.jsx'
import VulnerabilityCard from './components/VulnerabilityCard.jsx'
import NarasiPanel       from './components/NarasiPanel.jsx'
import { useAnalysis }   from './hooks/useAnalysis.js'
import { MOCK_CITIES }   from './lib/mockData.js'
import { useTheme }      from './lib/ThemeContext.jsx'

const TABS = [
  { id: 'map',    label: 'Peta',     icon: Map },
  { id: 'alerts', label: 'Alert',    icon: Bell },
  { id: 'score',  label: 'Skor',     icon: BarChart2 },
  { id: 'narasi', label: 'Briefing', icon: MessageSquare },
]

function SectionTitle({ icon: Icon, title, badge }) {
  const { theme } = useTheme()
  const isDark    = theme === 'dark'
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <Icon size={14} className="text-blue-500" />
        <h2 className={clsx(
          'text-xs font-semibold uppercase tracking-wider',
          isDark ? 'text-gray-300' : 'text-gray-600'
        )}>
          {title}
        </h2>
      </div>
      {badge != null && (
        <span className="bg-red-500/20 text-red-400 border border-red-500/30
                         text-xs px-2 py-0.5 rounded-full font-semibold">
          {badge}
        </span>
      )}
    </div>
  )
}

export default function App() {
  const [selectedCity, setSelectedCity] = useState('semarang')
  const [activeTab,    setActiveTab]    = useState('map')
  const { theme }   = useTheme()
  const isDark      = theme === 'dark'
  const USE_MOCK    = import.meta.env.VITE_USE_MOCK === 'true'

  const { alerts, weather, vulnerability, narasi, loading, isLoading, lastUpdated, refresh }
    = useAnalysis(selectedCity)

  // ── Theme-aware class helpers ──────────────────────────────────────────────
  const bg      = isDark ? 'bg-gray-950' : 'bg-slate-50'
  const sidebarBg = isDark ? 'bg-gray-900' : 'bg-white'
  const border  = isDark ? 'border-gray-800' : 'border-gray-200'
  const text    = isDark ? 'text-gray-100' : 'text-gray-900'
  const stripBg = isDark ? 'bg-gray-900/80' : 'bg-white/90'

  return (
    <div className={clsx('flex flex-col h-screen overflow-hidden', bg, text)}>

      {/* ── Header ── */}
      <Header
        selectedCity={selectedCity}
        cities={MOCK_CITIES}
        onCityChange={setSelectedCity}
        onRefresh={refresh}
        isLoading={isLoading}
        lastUpdated={lastUpdated}
        isLive={!USE_MOCK}
      />

      {/* ── Weather Bar — strip cuaca real-time dari BMKG ── */}
      <WeatherBar
        data={weather}
        loading={loading.weather}
        isDark={isDark}
      />

      {/* ── Mobile tab bar ── */}
      <div className={clsx(
        'flex lg:hidden border-b shrink-0',
        sidebarBg, border
      )}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              'flex-1 flex flex-col items-center gap-1 py-2 text-xs transition-colors',
              activeTab === id
                ? 'text-blue-500 border-b-2 border-blue-500'
                : isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* ── Main layout ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left sidebar */}
        <aside className={clsx(
          'w-80 shrink-0 border-r flex-col overflow-y-auto',
          sidebarBg, border,
          activeTab !== 'map' ? 'flex' : 'hidden',
          'lg:flex'
        )}>
          <div className="p-4 space-y-5">

            <section>
              <SectionTitle icon={Bell} title="BMKG Alerts" badge={alerts?.flood_alerts} />
              <AlertPanel data={alerts} loading={loading.alerts} isDark={isDark} />
            </section>

            <section className={clsx('border-t pt-5', border)}>
              <SectionTitle icon={BarChart2} title="Vulnerability Score" />
              <VulnerabilityCard data={vulnerability} loading={loading.vulnerability} isDark={isDark} />
            </section>

          </div>
        </aside>

        {/* Center map */}
        <main className={clsx(
          'flex-1 flex flex-col overflow-hidden',
          activeTab !== 'map' && 'hidden lg:flex'
        )}>
          {/* Map wrapper — height:0 + flex-1 = pattern yang reliable untuk Leaflet */}
          <div className="flex-1 p-3" style={{ minHeight: 0, height: 0 }}>
            <MapView selectedCity={selectedCity} />
          </div>

          {/* Status strip */}
          {vulnerability && (
            <div className={clsx(
              'px-4 py-2 border-t flex items-center gap-5 text-sm shrink-0',
              stripBg, border
            )}>
              <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Status:</span>
              <span className={clsx('font-bold',
                vulnerability.score >= 75 ? 'text-red-500'
                : vulnerability.score >= 50 ? 'text-orange-500'
                : vulnerability.score >= 25 ? 'text-yellow-500'
                : 'text-green-500'
              )}>
                {vulnerability.category}
              </span>

              <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Skor:</span>
              <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                {vulnerability.score}/100
              </span>

              <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Est. terdampak:</span>
              <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                {vulnerability.resource_needs?.estimated_affected?.toLocaleString('id-ID')} jiwa
              </span>

              {vulnerability.is_sample_data && (
                <span className="ml-auto text-yellow-500/60 text-xs">⚠️ Sample data</span>
              )}
            </div>
          )}
        </main>

        {/* Right sidebar — AI Briefing */}
        <aside className={clsx(
          'w-96 shrink-0 border-l flex-col overflow-y-auto',
          sidebarBg, border,
          activeTab === 'narasi' ? 'flex' : 'hidden',
          'lg:flex'
        )}>
          <div className="p-4">
            <SectionTitle icon={MessageSquare} title="AI Briefing" />
            <NarasiPanel
              narasi={narasi}
              vulnerability={vulnerability}
              loading={loading.narasi}
              isDark={isDark}
            />
          </div>
        </aside>

      </div>
    </div>
  )
}
