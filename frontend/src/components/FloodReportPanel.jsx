/**
 * FloodInputPanel.jsx
 * ───────────────────
 * Form input laporan lapangan dari koordinator BPBD.
 *
 * Koordinator BPBD bisa input:
 *   - Nama sungai + ketinggian muka air (TMA) saat ini
 *   - Level status (Normal/Waspada/Siaga/Awas)
 *   - Area yang sudah tergenang (opsional, bisa multiple)
 *
 * Ketika di-submit → vulnerability score langsung update
 * Sesuai Pasal 23 Peraturan BNPB No.2/2024 — BPBD wajib
 * memberi umpan balik kondisi lapangan ke sistem peringatan dini.
 */

import { useState, useEffect } from 'react'
import { Droplets, RotateCcw } from 'lucide-react'
import clsx from 'clsx'

// ── Level config sesuai BNPB No.2/2024 ───────────────────────────────────────
const RIVER_LEVELS = [
  {
    id: 'normal',
    label: '🟢 Normal',
    desc: 'TMA di bawah batas siaga',
    boost: 0,
    color: 'green',
    bg: { dark: 'bg-green-500/15 border-green-500/50', light: 'bg-green-50 border-green-300' },
    text: { dark: 'text-green-300', light: 'text-green-700' },
    active: {
      dark: 'bg-green-500/30 border-green-400 ring-2 ring-green-400/50',
      light: 'bg-green-100 border-green-500 ring-2 ring-green-300'
    },
  },
  {
    id: 'waspada',
    label: '🟡 Waspada',
    desc: 'TMA mendekati batas siaga',
    boost: 8,
    color: 'yellow',
    bg: { dark: 'bg-yellow-500/15 border-yellow-500/50', light: 'bg-yellow-50 border-yellow-300' },
    text: { dark: 'text-yellow-300', light: 'text-yellow-700' },
    active: {
      dark: 'bg-yellow-500/30 border-yellow-400 ring-2 ring-yellow-400/50',
      light: 'bg-yellow-100 border-yellow-500 ring-2 ring-yellow-300'
    },
  },
  {
    id: 'siaga',
    label: '🟠 Siaga',
    desc: 'TMA mencapai batas siaga',
    boost: 15,
    color: 'orange',
    bg: { dark: 'bg-orange-500/15 border-orange-500/50', light: 'bg-orange-50 border-orange-300' },
    text: { dark: 'text-orange-300', light: 'text-orange-700' },
    active: {
      dark: 'bg-orange-500/30 border-orange-400 ring-2 ring-orange-400/50',
      light: 'bg-orange-100 border-orange-500 ring-2 ring-orange-300'
    },
  },
  {
    id: 'awas',
    label: '🔴 Awas',
    desc: 'TMA melampaui batas bahaya',
    boost: 25,
    color: 'red',
    bg: { dark: 'bg-red-500/15 border-red-500/50', light: 'bg-red-50 border-red-300' },
    text: { dark: 'text-red-300', light: 'text-red-700' },
    active: {
      dark: 'bg-red-500/30 border-red-400 ring-2 ring-red-400/50',
      light: 'bg-red-100 border-red-500 ring-2 ring-red-300'
    },
  },
]

function ReportCard({ report, isDark }) {
  const levelId = report.flood_level || report.river_level || 'normal'
  const level = RIVER_LEVELS.find(l => l.id === levelId) || RIVER_LEVELS[0]
  const timeStr = new Date(report.reported_at).toLocaleTimeString('id-ID',
    { hour: '2-digit', minute: '2-digit' })
  const variant = isDark ? 'dark' : 'light'

  return (
    <div className={clsx(
      'p-3 rounded-xl border text-xs space-y-1',
      level.bg[variant]
    )}>
      <div className="flex items-center justify-between">
        <span className={clsx('font-semibold', level.text[variant])}>
          {level.label}
        </span>
        <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>{timeStr}</span>
      </div>
      <div className={clsx('font-medium', isDark ? 'text-gray-200' : 'text-gray-800')}>
        {report.desa_name ? `Desa/Kel. ${report.desa_name}` : (report.river_name || 'Desa/Wilayah')}
        {report.water_level_cm ? ` — ${report.water_level_cm} cm` : ''}
      </div>
      {report.kecamatan && (
        <div className={isDark ? 'text-gray-400' : 'text-gray-500'}>
          Kecamatan {report.kecamatan}
        </div>
      )}
      {report.notes && (
        <div className={clsx('text-[11px] italic', isDark ? 'text-gray-400' : 'text-gray-500')}>
          &ldquo;{report.notes}&rdquo;
        </div>
      )}
      {report.flooded_areas?.length > 0 && (
        <div className={isDark ? 'text-gray-400' : 'text-gray-500'}>
          {report.flooded_areas.length} area tergenang
        </div>
      )}
      <div className={clsx('font-medium', level.text[variant])}>
        +{report.boost_score} poin ke skor risiko
      </div>
    </div>
  )
}


// ── Main Component ────────────────────────────────────────────────────────────
export default function FloodReportPanel({
  city,
  reports = [],
  loading = false,
  isDark = true,
  onClear,
}) {
  const [riverName, setRiverName] = useState('')

  // Reset selected river ketika kota berubah
  useEffect(() => { setRiverName('') }, [city])

  return (
    <div className="space-y-4">
      {/* Laporan terbaru */}
      {reports.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className={clsx('text-xs font-semibold uppercase tracking-wider',
              isDark ? 'text-gray-500' : 'text-gray-400'
            )}>
              Laporan Terbaru ({reports.length})
            </p>
            <button
              type="button"
              onClick={onClear}
              className={clsx(
                'flex items-center gap-1 text-xs transition-colors',
                isDark
                  ? 'text-gray-600 hover:text-gray-400'
                  : 'text-gray-400 hover:text-gray-600'
              )}
            >
              <RotateCcw size={11} />
              Reset
            </button>
          </div>
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {reports.map(r => (
              <ReportCard key={r.id} report={r} isDark={isDark} />
            ))}
          </div>
        </div>
      )}

      {reports.length === 0 && !loading && (
        <div className={clsx(
          'text-center py-6 text-xs',
          isDark ? 'text-gray-600' : 'text-gray-400'
        )}>
          <Droplets size={22} className="mx-auto mb-2 opacity-30" />
          <p>Belum ada laporan lapangan</p>
          {/* <p className="mt-0.5 opacity-60">
            Submit laporan untuk update skor secara real-time
          </p> */}
        </div>
      )}
    </div>
  )
}
