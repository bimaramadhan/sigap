/**
 * WeatherBar.jsx
 * ──────────────
 * Strip horizontal yang menampilkan kondisi cuaca real-time dari BMKG
 * dan pengaruhnya terhadap vulnerability score.
 *
 * Ditampilkan antara Header dan konten utama — selalu terlihat.
 * Desain: compact, satu baris, color-coded per risk level.
 */

import { Cloud, Droplets, TrendingUp, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

const RISK_CONFIG = {
  extreme: { bg: 'bg-red-500/20 border-red-500/40',    text: 'text-red-300',    badgeBg: 'bg-red-500/30',    label: 'EKSTREM'  },
  high:    { bg: 'bg-orange-500/15 border-orange-500/35', text: 'text-orange-300', badgeBg: 'bg-orange-500/25', label: 'TINGGI'   },
  medium:  { bg: 'bg-yellow-500/15 border-yellow-500/35', text: 'text-yellow-300', badgeBg: 'bg-yellow-500/25', label: 'SEDANG'   },
  low:     { bg: 'bg-blue-500/10 border-blue-500/25',   text: 'text-blue-300',   badgeBg: 'bg-blue-500/20',   label: 'RINGAN'   },
  none:    { bg: 'bg-gray-800/50 border-gray-700/50',   text: 'text-gray-400',   badgeBg: 'bg-gray-700/50',   label: 'CERAH'    },
}

const RISK_CONFIG_LIGHT = {
  extreme: { bg: 'bg-red-50 border-red-200',      text: 'text-red-700',    badgeBg: 'bg-red-100',    label: 'EKSTREM' },
  high:    { bg: 'bg-orange-50 border-orange-200', text: 'text-orange-700', badgeBg: 'bg-orange-100', label: 'TINGGI'  },
  medium:  { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700', badgeBg: 'bg-yellow-100', label: 'SEDANG'  },
  low:     { bg: 'bg-blue-50 border-blue-200',     text: 'text-blue-700',   badgeBg: 'bg-blue-100',   label: 'RINGAN'  },
  none:    { bg: 'bg-gray-50 border-gray-200',     text: 'text-gray-500',   badgeBg: 'bg-gray-100',   label: 'CERAH'   },
}

export default function WeatherBar({ data, loading, isDark }) {
  const configs = isDark ? RISK_CONFIG : RISK_CONFIG_LIGHT
  const risk    = data?.weather_risk ?? 'none'
  const cfg     = configs[risk] ?? configs.none

  if (loading && !data) {
    return (
      <div className={clsx(
        'border-b px-5 py-2 flex items-center gap-3',
        isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'
      )}>
        <div className={clsx('h-4 w-48 rounded animate-pulse',
          isDark ? 'bg-gray-800' : 'bg-gray-200'
        )} />
        <div className={clsx('h-4 w-32 rounded animate-pulse',
          isDark ? 'bg-gray-800' : 'bg-gray-200'
        )} />
      </div>
    )
  }

  if (!data) return null

  const rainfall    = data.rainfall_12h_mm ?? 0
  const boost       = data.boost_score ?? 0
  const desc        = data.worst_weather_desc ?? 'Tidak diketahui'
  const emoji       = data.worst_weather_emoji ?? '🌡️'
  const kecCount    = data.kecamatan_count ?? 0
  const fetchedAt   = data.fetched_at
    ? new Date(data.fetched_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className={clsx(
      'border-b px-5 py-2 flex items-center gap-4 text-xs shrink-0 transition-colors',
      cfg.bg,
      isDark ? 'border-b' : 'border-b',
    )}>
      {/* Emoji + kondisi */}
      <div className="flex items-center gap-1.5">
        <span className="text-base leading-none">{emoji}</span>
        <span className={clsx('font-semibold', cfg.text)}>{desc}</span>
      </div>

      {/* Divider */}
      <span className={isDark ? 'text-gray-700' : 'text-gray-300'}>|</span>

      {/* Rainfall */}
      <div className="flex items-center gap-1.5">
        <Droplets size={12} className={cfg.text} />
        <span className={cfg.text}>
          {rainfall.toFixed(1)} mm/12jam
        </span>
      </div>

      {/* Risk badge */}
      <span className={clsx(
        'px-2 py-0.5 rounded-full font-bold tracking-wide',
        cfg.badgeBg, cfg.text
      )}>
        {cfg.label}
      </span>

      {/* Score boost */}
      {boost > 0 && (
        <div className="flex items-center gap-1">
          <TrendingUp size={12} className={cfg.text} />
          <span className={clsx('font-semibold', cfg.text)}>
            +{boost} poin ke skor
          </span>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Kecamatan coverage + waktu */}
      <div className={clsx('flex items-center gap-3', isDark ? 'text-gray-500' : 'text-gray-400')}>
        {kecCount > 0 && (
          <span className="flex items-center gap-1">
            <Cloud size={11} />
            {kecCount} kecamatan
          </span>
        )}
        {fetchedAt && (
          <span className="flex items-center gap-1">
            <RefreshCw size={10} />
            {fetchedAt}
          </span>
        )}
        <span>BMKG Prakiraan</span>
      </div>
    </div>
  )
}
