import { Bot, FileText, Zap, ChevronDown, ChevronUp, Package } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

function ResourceRow({ label, value, isDark }) {
  return (
    <div className={clsx(
      'flex items-center justify-between py-1.5 border-b last:border-0',
      isDark ? 'border-gray-800' : 'border-gray-100'
    )}>
      <span className={clsx('text-sm', isDark ? 'text-gray-400' : 'text-gray-500')}>
        {label}
      </span>
      <span className={clsx('text-sm font-semibold',
        isDark ? 'text-white' : 'text-gray-900'
      )}>
        {typeof value === 'number' ? value.toLocaleString('id-ID') : value}
      </span>
    </div>
  )
}

export default function NarasiPanel({ narasi, vulnerability, loading, isDark }) {
  const [showResources, setShowResources] = useState(false)

  if (loading) {
    return (
      <div className="space-y-2.5">
        {[1,2,3,4,5,6].map(i => (
          <div key={i} className={clsx(
            'h-3.5 rounded animate-pulse',
            isDark ? 'bg-gray-800' : 'bg-gray-200',
            i % 3 === 0 ? 'w-3/4' : i % 2 === 0 ? 'w-4/5' : 'w-full'
          )} />
        ))}
      </div>
    )
  }

  if (!narasi) return null

  const isGemini  = narasi.source === 'gemini' || narasi.source === 'gemini_aistudio' || narasi.source === 'gemini_vertex'
  const isAIStudio = narasi.source === 'gemini_aistudio'
  const resources = vulnerability?.resource_needs
  const actions   = vulnerability?.priority_actions ?? []

  // Colors
  const narasiBg     = isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-blue-50/80 border-blue-200/60'
  const resourceBg   = isDark ? 'bg-gray-800/60' : 'bg-gray-50'
  const resourceBorder = isDark ? 'border-gray-700' : 'border-gray-200'
  const narasiText   = isDark ? 'text-gray-200' : 'text-gray-700'

  return (
    <div className="space-y-4">

      {/* Source badge */}
      <div className="flex items-center gap-2">
        <div className={clsx(
          'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
          isGemini
            ? isDark
              ? 'bg-blue-500/15 border-blue-500/40 text-blue-300'
              : 'bg-blue-50 border-blue-200 text-blue-700'
            : isDark
              ? 'bg-gray-700 border-gray-600 text-gray-300'
              : 'bg-gray-100 border-gray-300 text-gray-600'
        )}>
          {isGemini ? <Zap size={11} /> : <FileText size={11} />}
          {isAIStudio
            ? `Gemini AI Studio (Free)`
            : isGemini
            ? `Gemini Vertex AI`
            : 'Template Engine'
          }
        </div>
        <span className={clsx('text-xs', isDark ? 'text-gray-600' : 'text-gray-400')}>
          {new Date(narasi.generated_at).toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit'
          })}
        </span>
      </div>

      {/* Narasi text */}
      <div className={clsx(
        'border rounded-xl p-4 fade-in',
        narasiBg
      )}>
        <div className="flex items-start gap-2.5">
          <Bot size={15} className="text-blue-500 mt-0.5 shrink-0" />
          <p className={clsx('text-sm leading-relaxed whitespace-pre-line', narasiText)}>
            {narasi.narasi}
          </p>
        </div>
      </div>

      {/* Action items */}
      {actions.length > 0 && (
        <div className="space-y-1.5">
          <p className={clsx('text-xs uppercase tracking-wider mb-2',
            isDark ? 'text-gray-500' : 'text-gray-400'
          )}>
            Tindakan Prioritas
          </p>
          {actions.slice(0, 5).map((action, i) => {
            const isCritical = action.startsWith('🚨')
            const isWarning  = action.startsWith('⚠️')
            return (
              <div key={i} className={clsx(
                'flex items-start gap-2 text-sm rounded-lg px-3 py-2 border',
                isCritical
                  ? isDark
                    ? 'bg-red-500/10 border-red-500/30 text-red-200'
                    : 'bg-red-50 border-red-200 text-red-700'
                  : isWarning
                  ? isDark
                    ? 'bg-orange-500/10 border-orange-500/30 text-orange-200'
                    : 'bg-orange-50 border-orange-200 text-orange-700'
                  : isDark
                  ? 'bg-gray-800/60 border-gray-700 text-gray-300'
                  : 'bg-gray-50 border-gray-200 text-gray-600'
              )}>
                <span className="leading-snug">{action}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Resource needs collapsible */}
      {resources && (
        <div className={clsx('border rounded-xl overflow-hidden', resourceBorder)}>
          <button
            onClick={() => setShowResources(v => !v)}
            className={clsx(
              'w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors',
              resourceBg,
              isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-100'
            )}
          >
            <div className={clsx('flex items-center gap-2',
              isDark ? 'text-gray-300' : 'text-gray-700'
            )}>
              <Package size={14} />
              <span className="font-medium">Kebutuhan Resource</span>
            </div>
            <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>
              {showResources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </span>
          </button>

          {showResources && (
            <div className="px-4 py-2 fade-in">
              <ResourceRow label="Est. Jiwa Terdampak"   value={`${resources.estimated_affected?.toLocaleString('id-ID')} jiwa`} isDark={isDark} />
              <ResourceRow label="Perahu Evakuasi"        value={`${resources.perahu_minimal} unit`}    isDark={isDark} />
              <ResourceRow label="Tim SAR"                value={`${resources.tim_sar_minimal} tim`}    isDark={isDark} />
              <ResourceRow label="Titik Pengungsian"      value={`${resources.titik_evakuasi} titik`}   isDark={isDark} />
              <ResourceRow label="Stok Logistik"          value={`${resources.logistik_hari} hari`}     isDark={isDark} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
