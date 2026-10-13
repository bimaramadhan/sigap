/**
 * FloodInputPanel.jsx
 * ───────────────────
 * Form input laporan lapangan dari koordinator BPBD.
 *
 * Koordinator BPBD memilih satu desa/kelurahan. Kecamatan induk
 * ditampilkan dari katalog wilayah dan tidak bisa diubah.
 * Status banjir (Normal/Waspada/Siaga/Awas) menentukan boost skor.
 *
 * Kemanan & Otentikasi:
 * Sesuai Peraturan BNPB No.2/2024, fitur pelaporan lapangan ini diproteksi
 * menggunakan Login with Google agar hanya petugas BPBD yang sudah terotentikasi
 * yang dapat mengisi dan mengirimkan laporan.
 */

import { useMemo, useState, useEffect } from 'react'
import {
  Send,
  Droplets,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ShieldCheck,
  BadgeCheck,
  LogOut,
  Lock,
  Sparkles,
} from 'lucide-react'
import clsx from 'clsx'
import GoogleIcon from './GoogleIcon.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

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

function LevelButton({ level, selected, onSelect, isDark, disabled }) {
  const isActive = selected === level.id
  const variant  = isDark ? 'dark' : 'light'

  return (
    <button
      type="button"
      onClick={() => !disabled && onSelect(level.id)}
      disabled={disabled}
      className={clsx(
        'flex-1 flex flex-col items-center gap-1 p-2.5 rounded-xl border-2 transition-all duration-150',
        disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
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
      'p-3 rounded-xl border text-xs space-y-1.5 transition-all',
      level.bg[variant]
    )}>
      <div className="flex items-center justify-between">
        <span className={clsx('font-semibold', level.text[variant])}>
          {level.label}
        </span>
        <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>{timeStr}</span>
      </div>
      <div className={clsx('font-medium', isDark ? 'text-gray-200' : 'text-gray-800')}>
        {report.desa_name ? `Desa/Kel. ${report.desa_name}` : (report.river_name || 'Desa/Kelurahan')}
      </div>
      {report.kecamatan && (
        <div className={isDark ? 'text-gray-400' : 'text-gray-500'}>
          Kecamatan {report.kecamatan}
        </div>
      )}

      {/* Verified Officer Tag */}
      {report.reporter && (
        <div className={clsx(
          'flex items-center gap-1.5 pt-0.5 text-[11px]',
          isDark ? 'text-blue-300' : 'text-blue-700'
        )}>
          <ShieldCheck size={12} className="text-blue-500 shrink-0" />
          <span className="font-semibold truncate">Oleh: {report.reporter}</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-blue-500/20 text-blue-400 font-medium">
            Terverifikasi
          </span>
        </div>
      )}

      {report.notes && (
        <div className={clsx('text-[11px] italic', isDark ? 'text-gray-400' : 'text-gray-500')}>
          &ldquo;{report.notes}&rdquo;
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
  cityName,
  villages = [],
  reports  = [],
  loading  = false,
  isDark   = true,
  onSubmit,
  onClear,
}) {
  const { user, isAuthenticated, openAuthModal, logout } = useAuth()

  const [reporter,   setReporter]   = useState(user?.name || '')
  const [desaKode,   setDesaKode]   = useState('')
  const [filter,     setFilter]     = useState('')
  const [floodLevel, setFloodLevel] = useState('normal')
  const [notes,      setNotes]      = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted,  setSubmitted]  = useState(false)
  const [error,      setError]      = useState('')

  // Sync reporter name when user logs in / out
  useEffect(() => {
    if (user?.name) {
      setReporter(user.name)
    } else {
      setReporter('')
    }
  }, [user])

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
  const totalVillages   = useMemo(() => villages.reduce((acc, g) => acc + (g.villages?.length || 0), 0), [villages])
  const hasVillages     = totalVillages > 0

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Enforce authentication: only authenticated officers can submit
    if (!isAuthenticated || !user) {
      openAuthModal()
      return
    }

    if (!desaKode) {
      setError('Desa atau kelurahan wajib dipilih')
      return
    }
    setError('')
    setSubmitting(true)

    try {
      await onSubmit?.({
        city,
        reporter:    reporter || user.name || 'Koordinator BPBD',
        reporter_email: user.email || '',
        reporter_avatar: user.picture || '',
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
      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400',
    !isAuthenticated && 'cursor-not-allowed opacity-75'
  )

  const labelCls = clsx(
    'text-xs font-medium mb-1.5 block',
    isDark ? 'text-gray-400' : 'text-gray-600'
  )

  return (
    <div className="space-y-4">

      {/* ── Google Officer Auth Banner ─────────────────────────────────────── */}
      {!isAuthenticated ? (
        <div className={clsx(
          'p-4 rounded-2xl border transition-all space-y-3',
          isDark
            ? 'bg-gradient-to-r from-blue-950/40 via-slate-900 to-indigo-950/40 border-blue-500/30 text-white'
            : 'bg-gradient-to-r from-blue-50 via-white to-indigo-50/70 border-blue-200 text-gray-900 shadow-sm'
        )}>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white shadow-md flex items-center justify-center shrink-0 border border-gray-100">
              <GoogleIcon size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold">Login Petugas Diperlukan</h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  🔒 Khusus Petugas BPBD
                </span>
              </div>
              <p className={clsx('text-xs mt-1 leading-relaxed', isDark ? 'text-gray-300' : 'text-gray-600')}>
                Sesuai SOP BNPB No.2/2024, verifikasi akun Google diperlukan agar hanya petugas resmi yang dapat mengisi dan mengirim laporan validasi lapangan.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={openAuthModal}
            className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-xl bg-white hover:bg-gray-50 text-gray-800 font-semibold text-xs border border-gray-300 shadow-sm transition-all hover:shadow hover:scale-[1.005] active:scale-[0.99] cursor-pointer"
          >
            <GoogleIcon size={16} />
            <span>Login with Google untuk Mengisi Form</span>
          </button>
        </div>
      ) : (
        /* Logged In Officer Card */
        <div className={clsx(
          'p-3.5 rounded-2xl border transition-all flex items-center justify-between gap-3',
          isDark
            ? 'bg-blue-950/30 border-blue-500/30 text-blue-200'
            : 'bg-blue-50/80 border-blue-200 text-blue-900 shadow-sm'
        )}>
          <div className="flex items-center gap-3 min-w-0">
            <div className="relative shrink-0">
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-10 h-10 rounded-full object-cover border-2 border-blue-500 shrink-0"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
                  {user.name?.charAt(0) || 'P'}
                </div>
              )}
              <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-green-500 border-2 border-white dark:border-gray-900" title="Aktif" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className={clsx('font-bold text-xs md:text-sm truncate', isDark ? 'text-white' : 'text-gray-900')}>
                  {user.name}
                </span>
                <BadgeCheck size={15} className="text-blue-500 shrink-0" />
              </div>
              <p className={clsx('text-[11px] truncate', isDark ? 'text-blue-300/80' : 'text-blue-700/80')}>
                {user.role || 'Petugas Lapangan BPBD'} • {user.email}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={logout}
            title="Keluar / Ganti Akun"
            className={clsx(
              'flex items-center gap-1 px-2.5 py-1.5 rounded-xl border text-[11px] font-medium transition-all shrink-0 cursor-pointer',
              isDark
                ? 'bg-gray-800/80 border-gray-700 text-gray-300 hover:text-white hover:bg-gray-700'
                : 'bg-white border-gray-300 text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <LogOut size={12} />
            <span className="hidden sm:inline">Keluar</span>
          </button>
        </div>
      )}

      {/* ── Form Pelaporan Lapangan ────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Nama Petugas Field */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className={labelCls}>Nama Petugas</label>
            {isAuthenticated ? (
              <span className="text-[10px] flex items-center gap-1 text-green-500 font-medium">
                <BadgeCheck size={12} /> Google Verified
              </span>
            ) : (
              <span className="text-[10px] text-amber-500 font-medium flex items-center gap-1">
                <Lock size={10} /> Perlu Login
              </span>
            )}
          </div>
          <div className="relative">
            <input
              type="text"
              placeholder={isAuthenticated ? user?.name : 'Login with Google untuk mengisi'}
              value={reporter}
              onChange={e => setReporter(e.target.value)}
              disabled={!isAuthenticated}
              className={clsx(inputCls, isAuthenticated && 'font-medium')}
            />
          </div>
        </div>

        {/* Cari Desa Field */}
        <div>
          <label className={labelCls}>
            Cari desa / kelurahan {hasVillages ? <span className="opacity-75 font-normal">({totalVillages} desa di {villages.length} kecamatan)</span> : ''}
          </label>
          <input
            type="text"
            placeholder={isAuthenticated ? "Ketik nama desa atau kecamatan" : "Login Google terlebih dahulu"}
            value={filter}
            onChange={e => setFilter(e.target.value)}
            disabled={!hasVillages || !isAuthenticated}
            className={inputCls}
          />
        </div>

        {/* Pilihan Desa */}
        <div>
          <label className={labelCls}>
            Desa / Kelurahan * {cityName ? <span className="text-blue-500 font-semibold">({cityName})</span> : ''}
          </label>
          <select
            value={desaKode}
            onChange={e => setDesaKode(e.target.value)}
            required
            disabled={!hasVillages || !isAuthenticated}
            className={clsx(inputCls, isAuthenticated && 'cursor-pointer')}
          >
            <option value="">
              {!isAuthenticated
                ? '🔒 Login dengan Google untuk memilih desa...'
                : hasVillages
                  ? `Pilih desa / kelurahan (${totalVillages} desa)...`
                  : loading ? 'Memuat data desa...' : 'Belum ada data desa untuk wilayah ini'}
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

        {/* Status Banjir */}
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
                disabled={!isAuthenticated}
              />
            ))}
          </div>
          {floodLevel !== 'normal' && (
            <p className={clsx('text-xs mt-1.5', isDark ? 'text-gray-400' : 'text-gray-500')}>
              {selectedLevel.desc} — boost <span className="font-bold text-orange-400">+{selectedLevel.boost} poin</span>
            </p>
          )}
        </div>

        {/* Catatan Tambahan */}
        <div>
          <label className={labelCls}>Catatan Tambahan</label>
          <textarea
            rows={2}
            placeholder={isAuthenticated ? "Kondisi lapangan, jalur terputus, dll." : "Login Google untuk menambahkan catatan..."}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            disabled={!isAuthenticated}
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
            Laporan ini menambah <strong>+{selectedLevel.boost} poin</strong> ke skor {cityName || city}
            {selectedVillage ? ` dan kecamatan ${selectedVillage.kecamatan}` : ''}
          </div>
        )}

        {/* Submit or Google Login Button */}
        {!isAuthenticated ? (
          <button
            type="button"
            onClick={openAuthModal}
            className="w-full flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/25 active:scale-[0.99] transition-all cursor-pointer"
          >
            <GoogleIcon size={18} />
            <span>Login with Google untuk Submit Laporan</span>
          </button>
        ) : (
          <button
            type="submit"
            disabled={submitting || !desaKode || !hasVillages}
            className={clsx(
              'w-full flex items-center justify-center gap-2 py-2.5 px-4',
              'rounded-xl font-semibold text-sm text-white transition-all',
              submitting || !desaKode || !hasVillages
                ? 'bg-gray-600 cursor-not-allowed opacity-60'
                : 'bg-blue-600 hover:bg-blue-500 active:scale-[0.98] shadow-md shadow-blue-600/20 cursor-pointer'
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
                Mengirim Laporan...
              </>
            ) : (
              <>
                <Send size={15} />
                Kirim Laporan Lapangan ({user.name.split(' ')[0]})
              </>
            )}
          </button>
        )}
      </form>

      {/* Riwayat Laporan Lapangan */}
      {reports.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-dashed"
             style={{ borderColor: isDark ? '#374151' : '#e5e7eb' }}>
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
                'flex items-center gap-1 text-xs transition-colors cursor-pointer',
                isDark
                  ? 'text-gray-600 hover:text-gray-400'
                  : 'text-gray-400 hover:text-gray-600'
              )}
            >
              <RotateCcw size={11} />
              Reset
            </button>
          </div>
          <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
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
