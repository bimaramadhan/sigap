import { AlertTriangle, Bell, Clock, MapPin, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

const SEVERITY_CONFIG = {
  Extreme:  { bg: 'bg-red-500/15',    border: 'border-red-500/40',    text: 'text-red-300',    dot: 'bg-red-500',    label: 'Ekstrem', pulse: true  },
  Severe:   { bg: 'bg-orange-500/15', border: 'border-orange-500/40', text: 'text-orange-300', dot: 'bg-orange-500', label: 'Parah',   pulse: false },
  Moderate: { bg: 'bg-yellow-500/15', border: 'border-yellow-500/40', text: 'text-yellow-300', dot: 'bg-yellow-500', label: 'Sedang',  pulse: false },
  Minor:    { bg: 'bg-blue-500/15',   border: 'border-blue-500/40',   text: 'text-blue-300',   dot: 'bg-blue-500',   label: 'Ringan',  pulse: false },
  Unknown:  { bg: 'bg-gray-500/15',   border: 'border-gray-500/40',   text: 'text-gray-400',   dot: 'bg-gray-500',   label: '?',       pulse: false },
}

// Light mode overrides (lebih solid)
const SEVERITY_LIGHT = {
  Extreme:  { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700'    },
  Severe:   { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' },
  Moderate: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700' },
  Minor:    { bg: 'bg-blue-50',   border: 'border-blue-200',   text: 'text-blue-700'   },
  Unknown:  { bg: 'bg-gray-50',   border: 'border-gray-200',   text: 'text-gray-600'   },
}

function AlertItem({ alert, isDark }) {
  const [expanded, setExpanded] = useState(false)
  const darkCfg  = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.Unknown
  const lightCfg = SEVERITY_LIGHT[alert.severity]  ?? SEVERITY_LIGHT.Unknown
  const cfg      = isDark ? darkCfg : { ...darkCfg, ...lightCfg }

  const exp            = new Date(alert.expires)
  const isExpiringSoon = alert.expires && (exp - Date.now()) < 3600000

  return (
    <div className={clsx('border rounded-xl p-3 text-sm transition-all', cfg.bg, cfg.border)}>
      <div
        className="flex items-start justify-between gap-2 cursor-pointer select-none"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex items-start gap-2 flex-1 min-w-0">
          {/* Dot */}
          <div className="relative mt-1 shrink-0">
            <div className={clsx('w-2.5 h-2.5 rounded-full', darkCfg.dot)} />
            {darkCfg.pulse && (
              <div className={clsx('absolute inset-0 rounded-full animate-ping opacity-60', darkCfg.dot)} />
            )}
          </div>

          <div className="min-w-0 flex-1">
            <p className={clsx('font-semibold leading-snug', cfg.text)}>{alert.title}</p>
            <div className={clsx('flex items-center gap-3 mt-1 text-xs opacity-70', cfg.text)}>
              <span className="flex items-center gap-1">
                <MapPin size={10} />{alert.kecamatan_count} kecamatan
              </span>
              {alert.expires && (
                <span className={clsx(
                  'flex items-center gap-1',
                  isExpiringSoon && 'font-semibold opacity-100'
                )}>
                  <Clock size={10} />
                  {exp.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className={clsx(
            'text-xs px-1.5 py-0.5 rounded font-medium',
            isDark ? 'bg-black/20' : 'bg-white/60',
            cfg.text
          )}>
            {darkCfg.label}
          </span>
          <span className={clsx('opacity-50', cfg.text)}>
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </span>
        </div>
      </div>

      {expanded && (
        <div className={clsx('mt-2.5 pt-2.5 border-t space-y-1 text-xs opacity-80', cfg.text,
          isDark ? 'border-white/10' : 'border-black/10'
        )}>
          <p><span className="font-medium">Provinsi:</span> {alert.province}</p>
          {alert.effective && (
            <p><span className="font-medium">Mulai:</span>{' '}
              {new Date(alert.effective).toLocaleString('id-ID')}
            </p>
          )}
          {alert.expires && (
            <p><span className="font-medium">Berakhir:</span>{' '}
              {exp.toLocaleString('id-ID')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function AlertPanel({ data, loading, isDark }) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1,2,3].map(i => (
          <div key={i} className={clsx('h-16 rounded-xl animate-pulse',
            isDark ? 'bg-gray-800' : 'bg-gray-200'
          )} />
        ))}
      </div>
    )
  }

  if (!data) return null
  const { total_alerts, flood_alerts, alerts } = data

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="flex items-center gap-3 text-sm">
        <div className={clsx(
          'flex items-center gap-1.5 border rounded-lg px-2.5 py-1.5',
          isDark
            ? 'bg-red-500/10 border-red-500/30 text-red-400'
            : 'bg-red-50 border-red-200 text-red-600'
        )}>
          <AlertTriangle size={13} />
          <span className="font-semibold">{flood_alerts}</span>
          <span className="opacity-80">banjir</span>
        </div>
        <div className={clsx('flex items-center gap-1.5 text-xs',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>
          <Bell size={12} />
          <span>{total_alerts} total</span>
        </div>
      </div>

      {/* List */}
      {alerts.length === 0 ? (
        <div className={clsx('text-center py-8 text-sm',
          isDark ? 'text-gray-500' : 'text-gray-400'
        )}>
          <Bell size={24} className="mx-auto mb-2 opacity-30" />
          <p>Tidak ada alert banjir aktif</p>
          <p className="text-xs mt-1 opacity-60">Refresh setiap 5 menit</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-60 overflow-y-auto pr-0.5">
          {alerts.map(alert => (
            <AlertItem key={alert.id} alert={alert} isDark={isDark} />
          ))}
        </div>
      )}

      <p className={clsx('text-xs text-center', isDark ? 'text-gray-600' : 'text-gray-400')}>
        Sumber: BMKG Open Data API
      </p>
    </div>
  )
}
