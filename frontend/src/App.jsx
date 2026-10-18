import { useState, useCallback, useEffect } from 'react'
import { Bell, Map, BarChart2, MessageSquare, Droplets, ArrowUpRight } from 'lucide-react'
import clsx from 'clsx'

import Header from './components/Header.jsx'
import WeatherBar from './components/WeatherBar.jsx'
import MapView from './components/MapView.jsx'
import AlertPanel from './components/AlertPanel.jsx'
import VulnerabilityCard from './components/VulnerabilityCard.jsx'
import NarasiPanel from './components/NarasiPanel.jsx'
import ReportPage from './components/ReportPage.jsx'
import GoogleAuthModal from './components/GoogleAuthModal.jsx'
import { useAnalysis } from './hooks/useAnalysis.js'
import { useFloodReports } from './hooks/useFloodReports.js'
import { MOCK_CITIES } from './lib/mockData.js'
import { getCities, getCity } from './lib/api.js'
import { useTheme } from './lib/ThemeContext.jsx'
import { useLanguage } from './lib/LanguageContext.jsx'

// Mobile tabs — 5 tabs sekarang
const TABS = [
  { id: 'map', label: 'Peta', icon: Map },
  { id: 'alerts', label: 'Alert', icon: Bell },
  { id: 'score', label: 'Skor', icon: BarChart2 },
  { id: 'narasi', label: 'Briefing', icon: MessageSquare },
]

// ── Section title helper ──────────────────────────────────────────────────────
function SectionTitle({ icon: Icon, title, badge }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
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

  const [selectedCity, setSelectedCity] = useState('33.74')
  const [cities, setCities] = useState(MOCK_CITIES)
  const [cityMeta, setCityMeta] = useState(MOCK_CITIES[0])
  const [activeTab, setActiveTab] = useState('map')
  const [toast, setToast] = useState(null)
  const [mapEpoch, setMapEpoch] = useState(0)
  const { theme } = useTheme()
  const { t, fmtNum, lang: uiLang } = useLanguage()
  const isDark = theme === 'dark'
  const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

  const currentCityObj = cities.find(c => c.id === selectedCity) || MOCK_CITIES.find(c => c.id === selectedCity)
  const cityName = cityMeta?.label || currentCityObj?.label || selectedCity


  // ── Routing: '/' (Dashboard) atau '/report' (Halaman Laporan & Briefing) ────
  const [currentPath, setCurrentPath] = useState(() => {
    if (typeof window !== 'undefined') {
      const p = window.location.pathname.toLowerCase().replace(/\/+$/, '')
      return p === '/report' ? '/report' : '/'
    }
    return '/'
  })

  useEffect(() => {
    const handlePopState = () => {
      const p = window.location.pathname.toLowerCase().replace(/\/+$/, '')
      setCurrentPath(p === '/report' ? '/report' : '/')
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = useCallback((path) => {
    const target = path.toLowerCase().replace(/\/+$/, '') || '/'
    if (window.location.pathname !== target) {
      window.history.pushState(null, '', target)
    }
    setCurrentPath(target === '/report' ? '/report' : '/')
  }, [])


  useEffect(() => {
    let cancelled = false
    getCities().then(res => {
      if (cancelled) return
      const list = res.cities || []
      if (!list.length) return
      setCities(list)
      const found = list.find(city => city.id === '33.74') || list[0]
      setCityMeta(found)
      setSelectedCity(found.id)
    })
    return () => { cancelled = true }
  }, [])

  const handleCityChange = (id) => {
    setSelectedCity(id)
    const meta = cities.find(city => city.id === id)
    setCityMeta(meta || { id, label: id, bbox: null })
    if (!meta?.bbox) {
      getCity(id).then(detail => {
        setCityMeta(detail)
        setCities(prev => prev.map(city => city.id === id ? { ...city, bbox: detail.bbox } : city))
      }).catch(() => { })
    }
  }

  const located = cityMeta?.id === selectedCity
    && Array.isArray(cityMeta?.bbox)
    && cityMeta.bbox.length === 4
  const activeCity = located ? selectedCity : ''

  // ── Analysis hook ──────────────────────────────────────────────────────────
  const { alerts, weather, vulnerability, narasi, loading, isLoading, lastUpdated, refresh }
    = useAnalysis(activeCity, uiLang)

  // ── Flood reports hook ─────────────────────────────────────────────────────
  const handleRefresh = useCallback(() => {
    setMapEpoch(n => n + 1)
    refresh()
  }, [refresh])

  const onReportSuccess = useCallback(() => {
    showToast(t('toast.reportSent'), 'success')
    setMapEpoch(n => n + 1)
    // Delay sedikit supaya backend sempat proses sebelum refresh
    setTimeout(() => refresh(), 300)
  }, [refresh])

  const { villages, reports, kecamatanBoosts, submit: submitReport, clear: clearReports }
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
      showToast(t('toast.reportFailed'), 'error')
    }
  }

  // ── Theme helpers ──────────────────────────────────────────────────────────
  const bg = isDark ? 'bg-gray-950' : 'bg-slate-50'
  const sidebarBg = isDark ? 'bg-gray-900' : 'bg-white'
  const border = isDark ? 'border-gray-800' : 'border-gray-200'
  const text = isDark ? 'text-gray-100' : 'text-gray-900'
  const stripBg = isDark ? 'bg-gray-900/80' : 'bg-white/90'

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className={clsx('flex flex-col h-screen overflow-hidden', bg, text)}>

      {/* Header */}
      <Header
        selectedCity={selectedCity}
        cities={cities}
        onCityChange={handleCityChange}
        onRefresh={handleRefresh}
        isLoading={isLoading}
        lastUpdated={lastUpdated}
        isLive={!USE_MOCK}
        currentPath={currentPath}
        onNavigate={navigate}
      />

      {currentPath === '/report' ? (
        /* ── Report Page View: Hanya menampilkan Briefing dan Laporan UI ── */
        <ReportPage
          selectedCity={selectedCity}
          cityName={cityName}
          cities={cities}
          onCityChange={handleCityChange}
          narasi={narasi}
          vulnerability={vulnerability}
          loading={loading}
          villages={villages}
          reports={reports}
          onSubmitReport={handleSubmitReport}
          onClearReports={() => {
            clearReports()
            showToast(t('toast.reportCleared'), 'success')
          }}
          onNavigate={navigate}
        />
      ) : (
        /* ── Dashboard View: Peta, Alerts, Skor, dan Sidebar ── */
        <>
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
                {t(`tabs.${id}`)}
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
                  <SectionTitle icon={Bell} title={t('section.bmkgAlerts')} badge={alerts?.flood_alerts} />
                  <AlertPanel data={alerts} loading={loading.alerts} isDark={isDark} />
                </section>

                <section className={clsx('border-t pt-5', border)}>
                  <SectionTitle icon={BarChart2} title={t('section.vulnScore')} />
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
                <MapView
                  selectedCity={selectedCity}
                  cityName={cityName}
                  cityMeta={cityMeta}
                  refreshEpoch={mapEpoch}
                />
              </div>

              {/* Status strip */}
              {vulnerability && (
                <div className={clsx(
                  'px-4 py-2 border-t flex items-center gap-4 text-sm shrink-0 flex-wrap',
                  stripBg, border
                )}>
                  <div className="flex items-center gap-2">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('status.status')}</span>
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
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('status.score')}</span>
                    <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                      {vulnerability.score}/100
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('status.affected')}</span>
                    <span className={clsx('font-bold', isDark ? 'text-white' : 'text-gray-900')}>
                      {fmtNum(vulnerability.resource_needs?.estimated_affected)} {t('status.people')}
                    </span>
                  </div>

                  {/* Field report badge */}
                  {reports.length > 0 && (
                    <div className="flex items-center gap-1 bg-blue-500/15 border border-blue-500/30
                                text-blue-400 text-xs px-2 py-0.5 rounded-full">
                      <Droplets size={11} />
                      {reports.length} {t('status.fieldReports')}
                    </div>
                  )}

                  {vulnerability.is_sample_data && (
                    <span className="ml-auto text-yellow-500/60 text-xs">{t('status.sampleData')}</span>
                  )}
                </div>
              )}
            </main>

            {/* ── Right Sidebar: Briefing | Laporan ── */}
            <aside className={clsx(
              'w-96 shrink-0 border-l flex-col overflow-hidden',
              sidebarBg, border,
              // Mobile: tampil saat tab narasi
              activeTab === 'narasi' ? 'flex' : 'hidden',
              'lg:flex'
            )}>
              {/* Header sidebar */}
              <div className={clsx(
                'flex items-center gap-2 px-4 py-2.5 border-b shrink-0',
                isDark ? 'border-gray-800' : 'border-gray-200'
              )}>
                <MessageSquare size={13} className="text-blue-500" />
                <span className={clsx(
                  'text-xs font-semibold uppercase tracking-wider',
                  isDark ? 'text-gray-300' : 'text-gray-600'
                )}>{t('section.aiBriefing')}</span>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-4">
                <NarasiPanel
                  narasi={narasi}
                  vulnerability={vulnerability}
                  loading={loading.narasi}
                  isDark={isDark}
                />
              </div>
            </aside>

          </div>
        </>
      )}

      {/* Toast notification */}
      {toast && <Toast message={toast.message} type={toast.type} isDark={isDark} />}

      {/* Global Google Authentication Modal */}
      <GoogleAuthModal />

    </div>
  )
}
