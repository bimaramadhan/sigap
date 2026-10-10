/**
 * FloodInputPanel.jsx
 * ───────────────────
 * Form input laporan lapangan dari koordinator BPBD.
 *
 * Koordinator BPBD memilih satu desa/kelurahan. Kecamatan induk
 * ditampilkan dari katalog wilayah dan tidak bisa diubah.
 * Status banjir (Normal/Waspada/Siaga/Awas) menentukan boost skor.
 *
 * Ketika di-submit → vulnerability score kota naik, dan kecamatan
 * induk desa itu ditandai di peta.
 */

import { useMemo, useState, useEffect } from 'react'
import { Send, Droplets, CheckCircle2, AlertTriangle, RotateCcw } from 'lucide-react'
import clsx from 'clsx'

const FLOOD_LEVELS = [
  {
    id:     'normal',
    label:  '🟢 Normal',
    desc:   'Tidak ada genangan yang dilaporkan',
    boost:  0,
    bg:     { dark: 'bg-green-500/15 border-green-500/50',   light: 'bg-green-50 border-green-300' },
    text:   { dark: 'text-green-300', light: 'text-green-700' },
    active: { dark: 'bg-green-500/30 border-green-400 ring-2 ring-green-400/50',
              light: 'bg-green-100 border-green-500 ring-2 ring-green-300' },
  },
  {
    id:     'waspada',
    label:  '🟡 Waspada',
    desc:   'Genangan mulai terjadi di desa ini',
    boost:  8,
    bg:     { dark: 'bg-yellow-500/15 border-yellow-500/50',   light: 'bg-yellow-50 border-yellow-300' },
    text:   { dark: 'text-yellow-300', light: 'text-yellow-700' },
    active: { dark: 'bg-yellow-500/30 border-yellow-400 ring-2 ring-yellow-400/50',
              light: 'bg-yellow-100 border-yellow-500 ring-2 ring-yellow-300' },
  },
  {
    id:     'siaga',
    label:  '🟠 Siaga',
    desc:   'Genangan mengganggu aktivitas warga',
    boost:  15,
    bg:     { dark: 'bg-orange-500/15 border-orange-500/50',   light: 'bg-orange-50 border-orange-300' },
    text:   { dark: 'text-orange-300', light: 'text-orange-700' },
    active: { dark: 'bg-orange-500/30 border-orange-400 ring-2 ring-orange-400/50',
              light: 'bg-orange-100 border-orange-500 ring-2 ring-orange-300' },
  },
  {
    id:     'awas',
    label:  '🔴 Awas',
    desc:   'Genangan membahayakan dan perlu evakuasi',
    boost:  25,
    bg:     { dark: 'bg-red-500/15 border-red-500/50',   light: 'bg-red-50 border-red-300' },
    text:   { dark: 'text-red-300', light: 'text-red-700' },
    active: { dark: 'bg-red-500/30 border-red-400 ring-2 ring-red-400/50',
              light: 'bg-red-100 border-red-500 ring-2 ring-red-300' },
  },
]

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

function findVillage(groups, kode) {
  for (const group of groups) {
    const village = group.villages?.find(v => v.kode === kode)
    if (village) return { ...village, ...group }
  }
  return null
}

function filterGroups(groups, query) {
  const q = query.trim().toLowerCase()
  if (!q) return groups
  return groups
    .map(group => {
      const kecMatch = group.kecamatan.toLowerCase().includes(q)
        || (group.kota_administrasi ?? '').toLowerCase().includes(q)
      const villages = kecMatch
        ? group.villages
        : group.villages.filter(v =>
            v.nama.toLowerCase().includes(q) || v.kode.includes(q)
          )
      return { ...group, villages }
    })
    .filter(group => group.villages.length > 0)
}

function groupLabel(group, showKota) {
  if (showKota && group.kota_administrasi) {
    return `${group.kecamatan} — ${group.kota_administrasi}`
  }
  return group.kecamatan
}

function ReportCard({ report, isDark }) {
  const levelId = report.flood_level || report.river_level || 'normal'
  const level   = FLOOD_LEVELS.find(l => l.id === levelId) || FLOOD_LEVELS[0]
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
      <div className={isDark ? 'text-gray-300' : 'text-gray-700'}>
        {report.desa_name || report.river_name}
      </div>
      {report.kecamatan && (
        <div className={isDark ? 'text-gray-400' : 'text-gray-500'}>
          Kec. {report.kecamatan}
        </div>
      )}
      <div className={clsx('font-medium', level.text[variant])}>
        +{report.boost_score} poin ke skor risiko
      </div>
    </div>
  )
}

export default function FloodInputPanel({
  city,
  villages = [],
  reports  = [],
  loading  = false,
  isDark   = true,
  onSubmit,
  onClear,
}) {
  const [reporter,   setReporter]   = useState('')
  const [desaKode,   setDesaKode]   = useState('')
  const [filter,     setFilter]     = useState('')
  const [floodLevel, setFloodLevel] = useState('normal')
  const [notes,      setNotes]      = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted,  setSubmitted]  = useState(false)
  const [error,      setError]      = useState('')

  useEffect(() => {
    setDesaKode('')
    setFilter('')
  }, [city])

  const selectedLevel   = FLOOD_LEVELS.find(l => l.id === floodLevel) || FLOOD_LEVELS[0]
  const selectedVillage = findVillage(villages, desaKode)
  const showKota        = new Set(villages.map(g => g.kota_administrasi).filter(Boolean)).size > 1
  const visibleGroups = useMemo(() => {
    const filtered = filterGroups(villages, filter)
    if (!desaKode || findVillage(filtered, desaKode)) return filtered
    const selected = findVillage(villages, desaKode)
    if (!selected) return filtered
    const option = { kode: selected.kode, nama: selected.nama }
    const existing = filtered.find(g => g.kecamatan_kode === selected.kecamatan_kode)
    if (existing) {
      return filtered.map(g => (
        g.kecamatan_kode === selected.kecamatan_kode
          ? { ...g, villages: [...g.villages, option] }
          : g
      ))
    }
    return [
      ...filtered,
      {
        kecamatan: selected.kecamatan,
        kecamatan_kode: selected.kecamatan_kode,
        kota_administrasi: selected.kota_administrasi,
        villages: [option],
      },
    ]
  }, [villages, filter, desaKode])
  const hasVillages     = villages.some(g => g.villages?.length > 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!desaKode) {
      setError('Desa atau kelurahan wajib dipilih')
      return
    }
    setError('')
    setSubmitting(true)

    try {
      await onSubmit?.({
        city,
        reporter:    reporter || 'Koordinator BPBD',
        desa_kode:   desaKode,
        flood_level: floodLevel,
        notes,
      })
      setNotes('')
      setFloodLevel('normal')
      setSubmitted(true)
      setTimeout(() => setSubmitted(false), 3000)
    } catch {
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

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
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

        <div>
          <label className={labelCls}>Cari desa / kelurahan</label>
          <input
            type="text"
            placeholder="Ketik nama desa atau kecamatan"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            disabled={!hasVillages}
            className={inputCls}
          />
        </div>

        <div>
          <label className={labelCls}>Desa / Kelurahan *</label>
          <select
            value={desaKode}
            onChange={e => setDesaKode(e.target.value)}
            required
            disabled={!hasVillages}
            className={clsx(inputCls, 'cursor-pointer')}
          >
            <option value="">
              {hasVillages ? 'Pilih desa...' : 'Belum ada data desa untuk kota ini'}
            </option>
            {visibleGroups.map(group => (
              <optgroup key={group.kecamatan_kode} label={groupLabel(group, showKota)}>
                {group.villages.map(village => (
                  <option key={village.kode} value={village.kode}>
                    {village.nama}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          {selectedVillage && (
            <p className={clsx('text-xs mt-1.5', isDark ? 'text-gray-400' : 'text-gray-500')}>
              Kecamatan: <span className="font-semibold">{selectedVillage.kecamatan}</span>
            </p>
          )}
        </div>

        <div>
          <label className={labelCls}>Status Banjir *</label>
          <div className="grid grid-cols-4 gap-1.5">
            {FLOOD_LEVELS.map(level => (
              <LevelButton
                key={level.id}
                level={level}
                selected={floodLevel}
                onSelect={setFloodLevel}
                isDark={isDark}
              />
            ))}
          </div>
          {floodLevel !== 'normal' && (
            <p className={clsx('text-xs mt-1.5', isDark ? 'text-gray-400' : 'text-gray-500')}>
              {selectedLevel.desc} — boost <span className="font-bold text-orange-400">+{selectedLevel.boost} poin</span>
            </p>
          )}
        </div>

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

        {error && (
          <p className="text-red-400 text-xs flex items-center gap-1">
            <AlertTriangle size={12} /> {error}
          </p>
        )}

        {desaKode && floodLevel !== 'normal' && (
          <div className={clsx(
            'rounded-xl p-2.5 text-xs border',
            isDark
              ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
              : 'bg-blue-50 border-blue-200 text-blue-700'
          )}>
            <Droplets size={12} className="inline mr-1" />
            Laporan ini menambah <strong>+{selectedLevel.boost} poin</strong> ke skor {city}
            {selectedVillage ? ` dan kecamatan ${selectedVillage.kecamatan}` : ''}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || !desaKode || !hasVillages}
          className={clsx(
            'w-full flex items-center justify-center gap-2 py-2.5 px-4',
            'rounded-xl font-semibold text-sm text-white transition-all',
            submitting || !desaKode || !hasVillages
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
