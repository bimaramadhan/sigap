import { useState, useCallback } from 'react'
import { Bell, Map, BarChart2, MessageSquare, Droplets } from 'lucide-react'
import clsx from 'clsx'

import Header            from './components/Header.jsx'
import WeatherBar        from './components/WeatherBar.jsx'
import MapView           from './components/MapView.jsx'
import AlertPanel        from './components/AlertPanel.jsx'
import VulnerabilityCard from './components/VulnerabilityCard.jsx'
import NarasiPanel       from './components/NarasiPanel.jsx'
import FloodInputPanel   from './components/FloodInputPanel.jsx'
import { useAnalysis }   from './hooks/useAnalysis.js'
import { useFloodReports } from './hooks/useFloodReports.js'
import { MOCK_CITIES }   from './lib/mockData.js'
import { useTheme }      from './lib/ThemeContext.jsx'

// Mobile tabs — 5 tabs sekarang
const TABS = [
  { id: 'map',     label: 'Peta',    icon: Map },
  { id: 'alerts',  label: 'Alert',   icon: Bell },
  { id: 'score',   label: 'Skor',    icon: BarChart2 },
  { id: 'narasi',  label: 'Briefing',icon: MessageSquare },
  { id: 'laporan', label: 'Laporan', icon: Droplets },
]

// ── Section title helper ──────────────────────────────────────────────────────
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

// ── Right sidebar tab bar ─────────────────────────────────────────────────────
function RightTabBar({ active, onChange, isDark, reportCount }) {
  const tabs = [
    { id: 'briefing', label: 'AI Briefing',     icon: MessageSquare },
    { id: 'laporan',  label: 'Laporan Lapangan', icon: Droplets,    badge: reportCount },
  ]
  return (
    <div className={clsx(
      'flex border-b shrink-0',
      isDark ? 'border-gray-800' : 'border-gray-200'
    )}>
      {tabs.map(({ id, label, icon: Icon, badge }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={clsx(
            'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium',
            'transition-colors border-b-2',
            active === id
              ? isDark
                ? 'text-blue-400 border-blue-500'
                : 'text-blue-600 border-blue-500'
              : isDark
              ? 'text-gray-500 border-transparent hover:text-gray-300'
              : 'text-gray-400 border-transparent hover:text-gray-600'
          )}
        >
          <Icon size={13} />
          {label}
          {badge > 0 && (
            <span className="bg-blue-500/20 text-blue-400 text-xs px-1.5 rounded-full font-bold">
              {badge}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

// ── Toast notification ────────────────────────────────────────────────────────
function Toast({ message, type, isDark }) {
  if (!message) return null
  return (
    <div className={clsx(
      'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
      'flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-xl',
      'text-sm font-medium animate-bounce-in',
      type === 'success'
        ? isDark ? 'bg-green-500/90 text-white' : 'bg-green-500 text-white'
        : isDark ? 'bg-red-500/90 text-white' : 'bg-red-500 text-white'
    )}>
      {type === 'success' ? '✅' : '❌'} {message}
    </div>
  )
}


// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [selectedCity, setSelectedCity] = useState('semarang')
  const [activeTab,    setActiveTab]    = useState('map')
  const [rightTab,     setRightTab]     = useState('briefing')
  const [toast,        setToast]        = useState(null)
  const { theme }  = useTheme()
  const isDark     = theme === 'dark'
  const USE_MOCK   = import.meta.env.VITE_USE_MOCK === 'true'

  // ── Analysis hook ──────────────────────────────────────────────────────────
  const { alerts, weather, vulnerability, narasi, loading, isLoading, lastUpdated, refresh }
    = useAnalysis(selectedCity)

  // ── Flood reports hook ─────────────────────────────────────────────────────
  const onReportSuccess = useCallback(() => {
    showToast('Laporan terkirim! Skor risiko diperbarui.', 'success')
    // Delay sedikit supaya backend sempat proses sebelum refresh
    setTimeout(() => refresh(), 300)
  }, [refresh])

  const { rivers, reports, submit: submitReport, clear: clearReports }
    = useFloodReports(selectedCity, onReportSuccess)

  // ── Toast helper ───────────────────────────────────────────────────────────
  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSubmitReport = async (data) => {
    try {
      await submitReport(data)
    } catch {
      showToast('Gagal mengirim laporan.', 'error')
    }
  }

  // ── Theme helpers ──────────────────────────────────────────────────────────
  const bg        = isDark ? 'bg-gray-950' : 'bg-slate-50'
  const sidebarBg = isDark ? 'bg-gray-900' : 'bg-white'
  const border    = isDark ? 'border-gray-800' : 'border-gray-200'
  const text      = isDark ? 'text-gray-100' : 'text-gray-900'
  const stripBg   = isDark ? 'bg-gray-900/80' : 'bg-white/90'

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className={clsx('flex flex-col h-screen overflow-hidden', bg, text)}>

      {/* Header */}
      <Header
        selectedCity={selectedCity}
        cities={MOCK_CITIES}
        onCityChange={setSelectedCity}
        onRefresh={refresh}
        isLoading={isLoading}
        lastUpdated={lastUpdated}
        isLive={!USE_MOCK}
      />

      {/* Weather Bar */}
      <WeatherBar data={weather} loading={loading.weather} isDark={isDark} />

      {/* Mobile tab bar */}
      <div className={clsx('flex lg:hidden border-b shrink-0', sidebarBg, border)}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              'flex-1 flex flex-col items-center gap-0.5 py-2 text-xs transition-colors',
              activeTab === id
                ? 'text-blue-500 border-b-2 border-blue-500'
                : isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left Sidebar: Alerts + Vulnerability ── */}
        <aside className={clsx(
          'w-80 shrink-0 border-r flex-col overflow-y-auto',
          sidebarBg, border,
          activeTab !== 'map' && activeTab !== 'narasi' && activeTab !== 'laporan'
            ? 'flex' : 'hidden',
          'lg:flex'
        )}>
          <div className="p-4 space-y-5">
            <section>
              <SectionTitle icon={Bell} title="BMKG Alerts" badge={alerts?.flood_alerts} />
              <AlertPanel data={alerts} loading={loading.alerts} isDark={isDark} />
            </section>

            <section className={clsx('border-t pt-5', border)}>
              <SectionTitle icon={BarChart2} title="Vulnerability Score" />
              <VulnerabilityCard
                data={vulnerability}
                loading={loading.vulnerability}
                isDark={isDark}
              />
            </section>
          </div>
        </aside>

        {/* ── Center: Map ── */}
        <main className={clsx(
          'flex-1 flex flex-col overflow-hidden',
          activeTab !== 'map' && 'hidden lg:flex'
        )}>
          <div className="flex-1 p-3" style={{ minHeight: 0, height: 0 }}>
            <MapView selectedCity={selectedCity} />
          </div>

          {/* Status strip */}
          {vulnerability && (
            <div className={clsx(
              'px-4 py-2 border-t flex items-center gap-4 text-sm shrink-0 flex-wrap',
              stripBg, border
            )}>
              <div className="flex items-center gap-2">
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Status:</span>
                <span className={clsx('font-bold',
                  vulnerability.score >= 75 ? 'text-red-500'
                  : vulnerability.score >= 50 ? 'text-orange-500'
                  : vulnerability.score >= 25 ? 'text-yellow-500'
                  : 'text-green-500'
                )}>
                  {vulnerability.category}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Skor:</span>
                <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                  {vulnerability.score}/100
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Est. terdampak:</span>
                <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                  {vulnerability.resource_needs?.estimated_affected?.toLocaleString('id-ID')} jiwa
                </span>
              </div>

              {/* Field report badge */}
              {reports.length > 0 && (
                <div className="flex items-center gap-1 bg-blue-500/15 border border-blue-500/30
                                text-blue-400 text-xs px-2 py-0.5 rounded-full">
                  <Droplets size={11} />
                  {reports.length} laporan lapangan
                </div>
              )}

              {vulnerability.is_sample_data && (
                <span className="ml-auto text-yellow-500/60 text-xs">⚠️ Sample data</span>
              )}
            </div>
          )}
        </main>

        {/* ── Right Sidebar: Briefing | Laporan ── */}
        <aside className={clsx(
          'w-96 shrink-0 border-l flex-col overflow-hidden',
          sidebarBg, border,
          // Mobile: tampil saat tab narasi atau laporan
          (activeTab === 'narasi' || activeTab === 'laporan') ? 'flex' : 'hidden',
          'lg:flex'
        )}>
          {/* Tab switcher di dalam right sidebar */}
          <RightTabBar
            active={activeTab === 'laporan' ? 'laporan' : rightTab}
            onChange={(t) => {
              setRightTab(t)
              // Sync mobile tab juga
              if (t === 'laporan') setActiveTab('laporan')
              else setActiveTab('narasi')
            }}
            isDark={isDark}
            reportCount={reports.length}
          />

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {(activeTab === 'laporan' || rightTab === 'laporan') && activeTab !== 'narasi' ? (
              // Panel Laporan Lapangan
              <>
                <SectionTitle icon={Droplets} title="Laporan Lapangan BPBD" />
                <FloodInputPanel
                  city={selectedCity}
                  rivers={rivers}
                  reports={reports}
                  isDark={isDark}
                  onSubmit={handleSubmitReport}
                  onClear={() => {
                    clearReports()
                    showToast('Laporan dihapus.', 'success')
                  }}
                />
              </>
            ) : (
              // Panel AI Briefing
              <>
                <SectionTitle icon={MessageSquare} title="AI Briefing" />
                <NarasiPanel
                  narasi={narasi}
                  vulnerability={vulnerability}
                  loading={loading.narasi}
                  isDark={isDark}
                />
              </>
            )}
          </div>
        </aside>

      </div>

      {/* Toast notification */}
      {toast && <Toast message={toast.message} type={toast.type} isDark={isDark} />}

    </div>
  )
}
