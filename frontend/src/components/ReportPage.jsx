/**
 * ReportPage.jsx
 * ──────────────
 * Halaman khusus laporan (/report) yang hanya menampilkan:
 * 1. AI Briefing & Rekomendasi Taktis (NarasiPanel)
 * 2. Form & Riwayat Laporan Lapangan BPBD (FloodInputPanel)
 *
 * Sesuai kebutuhan:
 * - Tidak menampilkan peta, alert list, atau vulnerability score card
 * - Dilengkapi banner ringkasan situasi bencana, status risiko, dan jumlah laporan
 * - Mendukung layout berdampingan (2-kolom) di desktop dan tab switcher di mobile
 */

import { useState, useRef, useEffect } from 'react'
import {
  MessageSquare,
  Droplets,
  ArrowLeft,
  Columns,
  Sparkles,
  ShieldAlert,
  ClipboardList,
  MapPin,
  BadgeCheck,
  LogOut,
  LogIn,
} from 'lucide-react'
import clsx from 'clsx'

import NarasiPanel from './NarasiPanel.jsx'
import FloodInputPanel from './FloodInputPanel.jsx'
import GoogleIcon from './GoogleIcon.jsx'
import { useTheme } from '../lib/ThemeContext.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

export default function ReportPage({
  selectedCity,
  cityName,
  cities = [],
  onCityChange,
  narasi,
  vulnerability,
  loading,
  villages = [],
  reports = [],
  onSubmitReport,
  onClearReports,
  onNavigate,
}) {
  const { theme } = useTheme()
  const { user, isAuthenticated, openAuthModal, logout } = useAuth()
  const isDark = theme === 'dark'

  // View mode: 'both' | 'briefing' | 'laporan'
  const [viewMode, setViewMode] = useState('both')

  // Searchable city combobox state
  const [citySearch, setCitySearch] = useState('')
  const [cityOpen, setCityOpen] = useState(false)
  const cityComboRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (cityComboRef.current && !cityComboRef.current.contains(e.target)) {
        setCityOpen(false)
        setCitySearch('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredCities = cities.filter((c) =>
    (c.label || c.name || c.id).toLowerCase().includes(citySearch.toLowerCase())
  )
  const selectedCityLabel = cities.find((c) => c.id === selectedCity)
  const displayCityName = selectedCityLabel ? (selectedCityLabel.label || selectedCityLabel.name || selectedCityLabel.id) : (cityName || selectedCity)

  const totalVillages = villages.reduce((acc, g) => acc + (g.villages?.length || 0), 0)
  const totalKecamatan = villages.length

  // Theme tokens
  const bgCard = isDark ? 'bg-gray-900/90' : 'bg-white'
  const border = isDark ? 'border-gray-800' : 'border-gray-200'
  const textMuted = isDark ? 'text-gray-400' : 'text-gray-500'

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* ── Top Header Banner ────────────────────────────────────────────── */}
        <div className={clsx(
          'p-5 md:p-6 rounded-2xl border shadow-sm transition-all',
          bgCard, border
        )}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

            {/* Title & Back Navigation */}
            <div className="space-y-2">
              <div>
                <h1 className={clsx('text-xl md:text-2xl font-bold tracking-tight',
                  isDark ? 'text-white' : 'text-gray-900'
                )}>
                  Laporan & Briefing Situasi Banjir
                </h1>
                <p className={clsx('text-xs md:text-sm mt-0.5', textMuted)}>
                  Intelijen AI kebencanaan dan umpan balik pelaporan lapangan tingkat desa/kelurahan BPBD
                </p>
              </div>

              {/* Kota / Kabupaten active mapping indicator */}
              <div className="flex flex-wrap items-center gap-2 pt-0.5">
                <div className={clsx(
                  'flex items-center gap-1.5 px-3 py-1 rounded-xl border text-xs',
                  isDark ? 'bg-gray-800/80 border-gray-700 text-gray-200' : 'bg-gray-100 border-gray-300 text-gray-800'
                )}>
                  <MapPin size={13} className="text-blue-500 shrink-0" />
                  <span className={textMuted}>Kota/Kab:</span>
                  {cities && cities.length > 0 && onCityChange ? (
                    <div ref={cityComboRef} className="relative">
                      <button
                        type="button"
                        onClick={() => { setCityOpen((o) => !o); setCitySearch('') }}
                        className={clsx(
                          'font-bold cursor-pointer focus:outline-none flex items-center gap-1 hover:opacity-80 transition-opacity',
                          isDark ? 'text-white' : 'text-gray-900'
                        )}
                      >
                        <span className="max-w-[160px] truncate">{displayCityName}</span>
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="10" height="10" viewBox="0 0 24 24"
                          fill="none" stroke="currentColor" strokeWidth="2.5"
                          strokeLinecap="round" strokeLinejoin="round"
                          className={clsx('shrink-0 transition-transform duration-200', cityOpen ? 'rotate-180' : '')}
                        >
                          <polyline points="6 9 12 15 18 9" />
                        </svg>
                      </button>

                      {cityOpen && (
                        <div className={clsx(
                          'absolute top-full left-0 mt-2 z-50 w-64 rounded-xl border shadow-2xl overflow-hidden',
                          isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
                        )}>
                          {/* Search input */}
                          <div className={clsx(
                            'px-3 py-2 border-b',
                            isDark ? 'border-gray-700' : 'border-gray-200'
                          )}>
                            <input
                              autoFocus
                              type="text"
                              value={citySearch}
                              onChange={(e) => setCitySearch(e.target.value)}
                              placeholder="Cari kota/kabupaten..."
                              className={clsx(
                                'w-full text-xs px-2.5 py-1.5 rounded-lg border focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition',
                                isDark
                                  ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-500'
                                  : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'
                              )}
                            />
                          </div>

                          {/* City list */}
                          <ul className="max-h-52 overflow-y-auto py-1 text-xs">
                            {filteredCities.length > 0 ? filteredCities.map((c) => (
                              <li
                                key={c.id}
                                onClick={() => {
                                  onCityChange(c.id)
                                  setCityOpen(false)
                                  setCitySearch('')
                                }}
                                className={clsx(
                                  'flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors',
                                  c.id === selectedCity
                                    ? isDark ? 'bg-blue-600/30 text-blue-300' : 'bg-blue-50 text-blue-700'
                                    : isDark ? 'text-gray-200 hover:bg-gray-800' : 'text-gray-800 hover:bg-gray-100'
                                )}
                              >
                                {c.id === selectedCity && (
                                  <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24"
                                    fill="none" stroke="currentColor" strokeWidth="3"
                                    strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                                    <polyline points="20 6 9 17 4 12" />
                                  </svg>
                                )}
                                <span className={c.id !== selectedCity ? 'ml-[14px]' : ''}>
                                  {c.label || c.name || c.id}
                                </span>
                              </li>
                            )) : (
                              <li className={clsx('px-3 py-3 text-center', isDark ? 'text-gray-500' : 'text-gray-400')}>
                                Tidak ditemukan
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="font-bold">{cityName || selectedCity}</span>
                  )}
                </div>

                <div className={clsx(
                  'flex items-center gap-1.5 px-3 py-1 rounded-xl border text-xs',
                  isDark ? 'bg-blue-500/10 border-blue-500/30 text-blue-300' : 'bg-blue-50 border-blue-200 text-blue-700'
                )}>
                  <span className="font-semibold">{totalVillages} Desa/Kelurahan</span>
                  <span className="opacity-75 font-normal">({totalKecamatan} Kecamatan)</span>
                </div>
              </div>
            </div>

            {/* Status badges & Quick stats */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Vulnerability status pill if available */}
              {vulnerability && (
                <div className={clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs',
                  vulnerability.score >= 75
                    ? isDark ? 'bg-red-500/15 border-red-500/40 text-red-300' : 'bg-red-50 border-red-200 text-red-700'
                    : vulnerability.score >= 50
                      ? isDark ? 'bg-orange-500/15 border-orange-500/40 text-orange-300' : 'bg-orange-50 border-orange-200 text-orange-700'
                      : vulnerability.score >= 25
                        ? isDark ? 'bg-yellow-500/15 border-yellow-500/40 text-yellow-300' : 'bg-yellow-50 border-yellow-200 text-yellow-700'
                        : isDark ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-green-50 border-green-200 text-green-700'
                )}>
                  <ShieldAlert size={14} />
                  <div>
                    <span className="font-semibold">Status: {vulnerability.category}</span>
                    <span className="ml-1 opacity-80">({vulnerability.score}/100)</span>
                  </div>
                </div>
              )}

              {/* Reports count */}
              <div className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold',
                reports.length > 0
                  ? isDark ? 'bg-blue-500/15 border-blue-500/40 text-blue-300' : 'bg-blue-50 border-blue-200 text-blue-700'
                  : isDark ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-gray-100 border-gray-300 text-gray-600'
              )}>
                <ClipboardList size={13} />
                <span>{reports.length} Laporan Lapangan</span>
              </div>

              {/* Officer Google Auth Status Pill */}
              {isAuthenticated && user ? (
                <div className={clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs transition-all shadow-sm',
                  isDark
                    ? 'bg-blue-950/40 border-blue-500/40 text-blue-200'
                    : 'bg-blue-50 border-blue-200 text-blue-900'
                )}>
                  {user.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name}
                      className="w-5 h-5 rounded-full object-cover border border-blue-400 shrink-0"
                    />
                  ) : (
                    <BadgeCheck size={14} className="text-blue-500 shrink-0" />
                  )}
                  <span className="font-semibold truncate max-w-[130px] sm:max-w-[180px]">
                    {user.name}
                  </span>
                  <button
                    type="button"
                    onClick={logout}
                    title="Keluar / Logout Petugas"
                    className="ml-0.5 text-gray-400 hover:text-red-400 transition-colors p-0.5 rounded cursor-pointer"
                  >
                    <LogOut size={12} />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={openAuthModal}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold shadow-sm transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer',
                    isDark
                      ? 'bg-gray-800 hover:bg-gray-750 border-gray-700 text-white'
                      : 'bg-white hover:bg-gray-50 border-gray-300 text-gray-800'
                  )}
                >
                  <GoogleIcon size={14} />
                  <span>Login Petugas</span>
                </button>
              )}
            </div>

          </div>

          {/* View Mode Switcher */}
          <div className="mt-5 pt-4 border-t border-dashed flex flex-wrap items-center justify-between gap-3"
            style={{ borderColor: isDark ? '#374151' : '#e5e7eb' }}>
            <span className={clsx('text-xs font-medium', textMuted)}>
              Pilihan Tampilan:
            </span>

            <div className={clsx(
              'flex items-center gap-1 p-1 rounded-xl border text-xs',
              isDark ? 'bg-gray-800/80 border-gray-700' : 'bg-gray-100 border-gray-300'
            )}>
              <button
                type="button"
                onClick={() => setViewMode('both')}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all',
                  viewMode === 'both'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <Columns size={13} />
                <span>Berdampingan</span>
              </button>

              <button
                type="button"
                onClick={() => setViewMode('briefing')}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all',
                  viewMode === 'briefing'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <MessageSquare size={13} />
                <span>AI Briefing</span>
              </button>

              <button
                type="button"
                onClick={() => setViewMode('laporan')}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all',
                  viewMode === 'laporan'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <Droplets size={13} />
                <span>Laporan Lapangan</span>
                {reports.length > 0 && (
                  <span className={clsx(
                    'text-[10px] px-1.5 py-0.2 rounded-full font-bold',
                    viewMode === 'laporan' ? 'bg-white/30 text-white' : 'bg-blue-500/20 text-blue-400'
                  )}>
                    {reports.length}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Main Content Grid ────────────────────────────────────────────── */}
        <div className={clsx(
          'transition-all duration-300',
          viewMode === 'both'
            ? 'grid grid-cols-1 lg:grid-cols-2 gap-6 items-start'
            : 'max-w-4xl mx-auto'
        )}>

          {/* ── Panel 1: AI Briefing ── */}
          {(viewMode === 'both' || viewMode === 'briefing') && (
            <div className={clsx(
              'rounded-2xl border p-5 md:p-6 shadow-sm space-y-4 fade-in',
              bgCard, border
            )}>
              <div className="flex items-center justify-between pb-3 border-b"
                style={{ borderColor: isDark ? '#1f2937' : '#f1f5f9' }}>
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <h2 className={clsx('text-sm md:text-base font-bold',
                      isDark ? 'text-white' : 'text-gray-900'
                    )}>
                      AI Briefing & Rekomendasi Taktis
                    </h2>
                    <p className={clsx('text-xs', textMuted)}>
                      Sintesis otomatis ancaman, langkah prioritas, dan alokasi sumber daya
                    </p>
                  </div>
                </div>
              </div>

              {/* Konten NarasiPanel */}
              <NarasiPanel
                narasi={narasi}
                vulnerability={vulnerability}
                loading={loading?.narasi}
                isDark={isDark}
              />
            </div>
          )}

          {/* ── Panel 2: Form & Riwayat Laporan Lapangan BPBD ── */}
          {(viewMode === 'both' || viewMode === 'laporan') && (
            <div className={clsx(
              'rounded-2xl border p-5 md:p-6 shadow-sm space-y-4 fade-in',
              bgCard, border
            )}>
              <div className="flex items-center justify-between pb-3 border-b"
                style={{ borderColor: isDark ? '#1f2937' : '#f1f5f9' }}>
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <ClipboardList size={16} />
                  </div>
                  <div>
                    <h2 className={clsx('text-sm md:text-base font-bold',
                      isDark ? 'text-white' : 'text-gray-900'
                    )}>
                      Laporan Lapangan Koordinator BPBD
                    </h2>
                    <p className={clsx('text-xs', textMuted)}>
                      Input kondisi genangan dan banjir per desa/kelurahan di {cityName || selectedCity} (BNPB No.2/2024)
                    </p>
                  </div>
                </div>
              </div>

              {/* Konten FloodInputPanel */}
              <FloodInputPanel
                city={selectedCity}
                cityName={cityName}
                villages={villages}
                reports={reports}
                loading={loading?.villages || loading?.reports}
                isDark={isDark}
                onSubmit={onSubmitReport}
                onClear={onClearReports}
              />
            </div>
          )}

        </div>

      </div>
    </div>
  )
}
