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
import { Send, Plus, Trash2, Droplets, CheckCircle2, AlertTriangle, RotateCcw } from 'lucide-react'
import clsx from 'clsx'

// ── Level config sesuai BNPB No.2/2024 ───────────────────────────────────────
const RIVER_LEVELS = [
  {
    id:     'normal',
    label:  '🟢 Normal',
    desc:   'TMA di bawah batas siaga',
    boost:  0,
    color:  'green',
    bg:     { dark: 'bg-green-500/15 border-green-500/50',   light: 'bg-green-50 border-green-300' },
    text:   { dark: 'text-green-300', light: 'text-green-700' },
    active: { dark: 'bg-green-500/30 border-green-400 ring-2 ring-green-400/50',
              light: 'bg-green-100 border-green-500 ring-2 ring-green-300' },
  },
  {
    id:     'waspada',
    label:  '🟡 Waspada',
    desc:   'TMA mendekati batas siaga',
    boost:  8,
    color:  'yellow',
    bg:     { dark: 'bg-yellow-500/15 border-yellow-500/50',   light: 'bg-yellow-50 border-yellow-300' },
    text:   { dark: 'text-yellow-300', light: 'text-yellow-700' },
    active: { dark: 'bg-yellow-500/30 border-yellow-400 ring-2 ring-yellow-400/50',
              light: 'bg-yellow-100 border-yellow-500 ring-2 ring-yellow-300' },
  },
  {
    id:     'siaga',
    label:  '🟠 Siaga',
    desc:   'TMA mencapai batas siaga',
    boost:  15,
    color:  'orange',
    bg:     { dark: 'bg-orange-500/15 border-orange-500/50',   light: 'bg-orange-50 border-orange-300' },
    text:   { dark: 'text-orange-300', light: 'text-orange-700' },
    active: { dark: 'bg-orange-500/30 border-orange-400 ring-2 ring-orange-400/50',
              light: 'bg-orange-100 border-orange-500 ring-2 ring-orange-300' },
  },
  {
    id:     'awas',
    label:  '🔴 Awas',
    desc:   'TMA melampaui batas bahaya',
    boost:  25,
    color:  'red',
    bg:     { dark: 'bg-red-500/15 border-red-500/50',   light: 'bg-red-50 border-red-300' },
    text:   { dark: 'text-red-300', light: 'text-red-700' },
    active: { dark: 'bg-red-500/30 border-red-400 ring-2 ring-red-400/50',
              light: 'bg-red-100 border-red-500 ring-2 ring-red-300' },
  },
]

// ── Sub-components ────────────────────────────────────────────────────────────
function LevelButton({ level, selected, onSelect, isDark }) {
  const isActive = selected === level.id
  const variant  = isDark ? 'dark' : 'light'

  return (
    <button
      type="button"
      onClick={() => onSelect(level.id)}
      className={clsx(
        'flex-1 flex flex-col items-center gap-1 p-2.5 rounded-xl border-2',
        'transition-all duration-150 cursor-pointer',
        isActive ? level.active[variant] : level.bg[variant]
      )}
    >
      <span className="text-base leading-none">{level.label.split(' ')[0]}</span>
      <span className={clsx('text-xs font-bold', level.text[variant])}>
        {level.label.split(' ')[1]}
      </span>
      {isActive && (
        <span className={clsx('text-xs font-semibold', level.text[variant])}>
          +{level.boost} poin
        </span>
      )}
    </button>
  )
}

function FloodAreaRow({ area, index, onChange, onRemove, isDark }) {
  const inputCls = clsx(
    'w-full px-2 py-1.5 rounded-lg border text-sm',
    'focus:outline-none focus:ring-1 focus:ring-blue-500',
    isDark
      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500'
      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
  )
  return (
    <div className={clsx(
      'p-2.5 rounded-xl border space-y-2',
      isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'
    )}>
      <div className="flex items-center justify-between">
        <span className={clsx('text-xs font-semibold',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>Area #{index + 1}</span>
        <button type="button" onClick={() => onRemove(index)}
          className="text-red-400 hover:text-red-300 transition-colors">
          <Trash2 size={13} />
        </button>
      </div>
      <input
        type="text"
        placeholder="RT/RW atau nama lokasi"
        value={area.name}
        onChange={e => onChange(index, 'name', e.target.value)}
        className={inputCls}
      />
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={clsx('text-xs mb-1 block',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>Kedalaman (cm)</label>
          <input
            type="number" min="1" max="500"
            placeholder="50"
            value={area.depth_cm || ''}
            onChange={e => onChange(index, 'depth_cm', parseInt(e.target.value) || 0)}
            className={inputCls}
          />
        </div>
        <div>
          <label className={clsx('text-xs mb-1 block',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>Est. Jiwa</label>
          <input
            type="number" min="0"
            placeholder="200"
            value={area.est_affected || ''}
            onChange={e => onChange(index, 'est_affected', parseInt(e.target.value) || 0)}
            className={inputCls}
          />
        </div>
      </div>
    </div>
  )
}

function ReportCard({ report, isDark }) {
  const level     = RIVER_LEVELS.find(l => l.id === report.river_level) || RIVER_LEVELS[0]
  const timeStr   = new Date(report.reported_at).toLocaleTimeString('id-ID',
    { hour: '2-digit', minute: '2-digit' })
  const variant   = isDark ? 'dark' : 'light'

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
      <div className={isDark ? 'text-gray-300' : 'text-gray-700'}>
        {report.river_name} — <strong>{report.water_level_cm} cm</strong>
      </div>
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
export default function FloodInputPanel({
  city,
  rivers   = [],
  reports  = [],
  loading  = false,
  isDark   = true,
  onSubmit,
  onClear,
}) {
  const [reporter,    setReporter]    = useState('')
  const [riverName,   setRiverName]   = useState('')
  const [waterLevel,  setWaterLevel]  = useState('')
  const [riverLevel,  setRiverLevel]  = useState('normal')
  const [floodAreas,  setFloodAreas]  = useState([])
  const [notes,       setNotes]       = useState('')
  const [submitting,  setSubmitting]  = useState(false)
  const [submitted,   setSubmitted]   = useState(false)
  const [error,       setError]       = useState('')

  // Reset selected river ketika kota berubah
  useEffect(() => { setRiverName('') }, [city])

  const selectedLevel = RIVER_LEVELS.find(l => l.id === riverLevel) || RIVER_LEVELS[0]

  // ── Area management ───────────────────────────────────────────────────────
  const addArea = () => setFloodAreas(prev => [
    ...prev, { name: '', depth_cm: 0, est_affected: 0 }
  ])

  const updateArea = (idx, field, value) => setFloodAreas(prev =>
    prev.map((a, i) => i === idx ? { ...a, [field]: value } : a)
  )

  const removeArea = (idx) => setFloodAreas(prev => prev.filter((_, i) => i !== idx))

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!riverName || !waterLevel) {
      setError('Nama sungai dan ketinggian air wajib diisi')
      return
    }
    setError('')
    setSubmitting(true)

    try {
      await onSubmit?.({
        city,
        reporter:       reporter || 'Koordinator BPBD',
        river_name:     riverName,
        water_level_cm: parseInt(waterLevel),
        river_level:    riverLevel,
        flooded_areas:  floodAreas.filter(a => a.name),
        notes,
      })
      // Reset form setelah berhasil
      setWaterLevel('')
      setFloodAreas([])
      setNotes('')
      setRiverLevel('normal')
      setSubmitted(true)
      setTimeout(() => setSubmitted(false), 3000)
    } catch (err) {
      setError('Gagal mengirim laporan. Coba lagi.')
    } finally {
      setSubmitting(false)
    }
  }

  const inputCls = clsx(
    'w-full px-3 py-2 rounded-xl border text-sm',
    'focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors',
    isDark
      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500'
      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
  )

  const labelCls = clsx(
    'text-xs font-medium mb-1.5 block',
    isDark ? 'text-gray-400' : 'text-gray-600'
  )

  // ── Preview boost ─────────────────────────────────────────────────────────
  const previewBoost = selectedLevel.boost + Math.min(floodAreas.filter(a=>a.name).length * 3, 15)

  return (
    <div className="space-y-4">

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">

        {/* Reporter */}
        <div>
          <label className={labelCls}>Nama Petugas</label>
          <input
            type="text"
            placeholder="Koordinator BPBD (opsional)"
            value={reporter}
            onChange={e => setReporter(e.target.value)}
            className={inputCls}
          />
        </div>

        {/* River + Level */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelCls}>Nama Sungai *</label>
            {rivers.length > 0 ? (
              <select
                value={riverName}
                onChange={e => setRiverName(e.target.value)}
                required
                className={clsx(inputCls, 'cursor-pointer')}
              >
                <option value="">Pilih sungai...</option>
                {rivers.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
                <option value="__other">Lainnya...</option>
              </select>
            ) : (
              <input
                type="text"
                placeholder="Nama sungai"
                value={riverName}
                onChange={e => setRiverName(e.target.value)}
                required
                className={inputCls}
              />
            )}
            {riverName === '__other' && (
              <input
                type="text"
                placeholder="Tulis nama sungai"
                className={clsx(inputCls, 'mt-1.5')}
                onChange={e => setRiverName(e.target.value)}
                autoFocus
              />
            )}
          </div>

          <div>
            <label className={labelCls}>TMA Saat Ini (cm) *</label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="999"
                placeholder="280"
                value={waterLevel}
                onChange={e => setWaterLevel(e.target.value)}
                required
                className={clsx(inputCls, 'pr-10')}
              />
              <span className={clsx(
                'absolute right-3 top-1/2 -translate-y-1/2 text-xs',
                isDark ? 'text-gray-500' : 'text-gray-400'
              )}>cm</span>
            </div>
          </div>
        </div>

        {/* Level selector */}
        <div>
          <label className={labelCls}>Status Level Sungai *</label>
          <div className="grid grid-cols-4 gap-1.5">
            {RIVER_LEVELS.map(level => (
              <LevelButton
                key={level.id}
                level={level}
                selected={riverLevel}
                onSelect={setRiverLevel}
                isDark={isDark}
              />
            ))}
          </div>
          {riverLevel !== 'normal' && (
            <p className={clsx('text-xs mt-1.5', isDark ? 'text-gray-400' : 'text-gray-500')}>
              {selectedLevel.desc} — boost <span className="font-bold text-orange-400">+{selectedLevel.boost} poin</span>
            </p>
          )}
        </div>

        {/* Flood areas */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className={labelCls.replace('mb-1.5', '')}>
              Area Tergenang
              <span className={clsx('ml-1 font-normal', isDark ? 'text-gray-500' : 'text-gray-400')}>
                (opsional, +3 poin/area)
              </span>
            </label>
            <button
              type="button"
              onClick={addArea}
              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-400 transition-colors"
            >
              <Plus size={12} />
              Tambah area
            </button>
          </div>

          {floodAreas.length > 0 && (
            <div className="space-y-2">
              {floodAreas.map((area, i) => (
                <FloodAreaRow
                  key={i}
                  area={area}
                  index={i}
                  onChange={updateArea}
                  onRemove={removeArea}
                  isDark={isDark}
                />
              ))}
            </div>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className={labelCls}>Catatan Tambahan</label>
          <textarea
            rows={2}
            placeholder="Kondisi lapangan, jalur terputus, dll."
            value={notes}
            onChange={e => setNotes(e.target.value)}
            className={clsx(inputCls, 'resize-none')}
          />
        </div>

        {/* Preview boost + Error */}
        {error && (
          <p className="text-red-400 text-xs flex items-center gap-1">
            <AlertTriangle size={12} /> {error}
          </p>
        )}

        {(riverLevel !== 'normal' || floodAreas.filter(a=>a.name).length > 0) && (
          <div className={clsx(
            'rounded-xl p-2.5 text-xs border',
            isDark
              ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
              : 'bg-blue-50 border-blue-200 text-blue-700'
          )}>
            <Droplets size={12} className="inline mr-1" />
            Laporan ini akan menambah <strong>+{previewBoost} poin</strong> ke skor risiko {city}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting || !riverName || !waterLevel}
          className={clsx(
            'w-full flex items-center justify-center gap-2 py-2.5 px-4',
            'rounded-xl font-semibold text-sm text-white transition-all',
            submitting || !riverName || !waterLevel
              ? 'bg-gray-600 cursor-not-allowed opacity-60'
              : 'bg-blue-600 hover:bg-blue-500 active:scale-[0.98]'
          )}
        >
          {submitted ? (
            <>
              <CheckCircle2 size={15} />
              Laporan Terkirim!
            </>
          ) : submitting ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Mengirim...
            </>
          ) : (
            <>
              <Send size={15} />
              Kirim Laporan Lapangan
            </>
          )}
        </button>
      </form>

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
          <p className="mt-0.5 opacity-60">
            Submit laporan untuk update skor secara real-time
          </p>
        </div>
      )}
    </div>
  )
}
