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

import { useState } from 'react'
import {
  MessageSquare,
  Droplets,
  ArrowLeft,
  Columns,
  Sparkles,
  ShieldAlert,
  ClipboardList,
} from 'lucide-react'
import clsx from 'clsx'

import NarasiPanel from './NarasiPanel.jsx'
import FloodInputPanel from './FloodInputPanel.jsx'
import { useTheme } from '../lib/ThemeContext.jsx'

export default function ReportPage({
  selectedCity,
  cityName,
  narasi,
  vulnerability,
  loading,
  rivers = [],
  reports = [],
  onSubmitReport,
  onClearReports,
  onNavigate,
}) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  // View mode: 'both' | 'briefing' | 'laporan'
  const [viewMode, setViewMode] = useState('both')

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
                  Intelijen AI kebencanaan dan umpan balik pelaporan lapangan BPBD — {cityName || selectedCity}
                </p>
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
                <Droplets size={13} />
                <span>{reports.length} Laporan Lapangan</span>
              </div>
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
                      Input kondisi TMA sungai dan genangan riil lapangan (BNPB No.2/2024)
                    </p>
                  </div>
                </div>
              </div>

              {/* Konten FloodInputPanel */}
              <FloodInputPanel
                city={selectedCity}
                rivers={rivers}
                reports={reports}
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
