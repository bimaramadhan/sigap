/**
 * GoogleAuthModal.jsx
 * ───────────────────
 * Modal dialog autentikasi Google untuk Petugas BPBD.
 *
 * Fitur:
 * - Menampilkan tombol Google Sign-In resmi jika VITE_GOOGLE_CLIENT_ID aktif.
 * - Pilihan cepat akun Google Petugas BPBD resmi (Budi Santoso, Siti Rahmawati, Ahmad Fauzi).
 * - Input kustom akun Google untuk demo fleksibel.
 * - Sesuai pedoman visual Google Sign-In & tema SIGAP (dark/light mode).
 */

import { useState, useEffect, useRef } from 'react'
import { X, ShieldCheck, UserCheck, ArrowRight, Sparkles, Building, BadgeCheck } from 'lucide-react'
import clsx from 'clsx'
import GoogleIcon from './GoogleIcon.jsx'
import { useAuth, DEMO_OFFICERS } from '../lib/AuthContext.jsx'
import { useTheme } from '../lib/ThemeContext.jsx'
import { useLanguage } from '../lib/LanguageContext.jsx'

export default function GoogleAuthModal() {
  const {
    isAuthModalOpen,
    closeAuthModal,
    hasGoogleClientId,
    isGoogleLoaded,
    handleGoogleCredentialResponse,
    loginWithProfile,
    loginWithCustomGoogle,
  } = useAuth()

  const { theme } = useTheme()
  const { t } = useLanguage()
  const isDark = theme === 'dark'

  const [mode, setMode] = useState('officers') // 'officers' | 'custom'
  const [customName, setCustomName] = useState('')
  const [customEmail, setCustomEmail] = useState('')
  const [customError, setCustomError] = useState('')
  const googleBtnRef = useRef(null)

  // Render official Google button if client ID is configured and GIS is loaded
  useEffect(() => {
    if (
      isAuthModalOpen &&
      hasGoogleClientId &&
      isGoogleLoaded &&
      googleBtnRef.current &&
      window.google?.accounts?.id
    ) {
      try {
        googleBtnRef.current.innerHTML = ''
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: isDark ? 'filled_black' : 'outline',
          size: 'large',
          width: '100%',
          text: 'signin_with',
          shape: 'pill',
          locale: 'id',
        })
      } catch (err) {
        console.warn('Error rendering GSI button:', err)
      }
    }
  }, [isAuthModalOpen, hasGoogleClientId, isGoogleLoaded, isDark])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isAuthModalOpen) {
        closeAuthModal()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isAuthModalOpen, closeAuthModal])

  if (!isAuthModalOpen) return null

  const handleCustomSubmit = (e) => {
    e.preventDefault()
    if (!customName.trim()) {
      setCustomError(t('auth.nameRequired'))
      return
    }
    if (!customEmail.trim() || !customEmail.includes('@')) {
      setCustomError(t('auth.emailInvalid'))
      return
    }
    setCustomError('')
    loginWithCustomGoogle({ name: customName, email: customEmail })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity animate-fade-in"
        onClick={closeAuthModal}
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        className={clsx(
          'relative w-full max-w-md rounded-3xl border shadow-2xl overflow-hidden transition-all z-10 animate-scale-up',
          isDark ? 'bg-gray-900 border-gray-800 text-white' : 'bg-white border-gray-200 text-gray-900'
        )}
      >
        {/* Top Header Decor */}
        <div className="relative px-6 pt-6 pb-4 border-b border-dashed"
             style={{ borderColor: isDark ? '#374151' : '#e5e7eb' }}>
          <button
            type="button"
            onClick={closeAuthModal}
            className={clsx(
              'absolute top-5 right-5 p-2 rounded-full transition-colors',
              isDark ? 'text-gray-400 hover:text-white hover:bg-gray-800' : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
            )}
            aria-label={t('auth.closeModal')}
          >
            <X size={18} />
          </button>

          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white shadow-md flex items-center justify-center shrink-0 border border-gray-100">
              <GoogleIcon size={26} />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="font-bold text-lg leading-snug">{t('auth.title')}</h3>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  {t('auth.badge')}
                </span>
              </div>
              <p className={clsx('text-xs mt-0.5', isDark ? 'text-gray-400' : 'text-gray-500')}>
                {t('auth.subtitle')}
              </p>
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">

          {/* Official Google Button (if client id set) */}
          {hasGoogleClientId && (
            <div className="space-y-2">
              <p className={clsx('text-xs font-semibold uppercase tracking-wider', isDark ? 'text-gray-400' : 'text-gray-500')}>
                {t('auth.googleLogin')}
              </p>
              <div ref={googleBtnRef} className="flex justify-center" />
              <div className="relative my-3">
                <div className="absolute inset-0 flex items-center">
                  <div className={clsx('w-full border-t', isDark ? 'border-gray-800' : 'border-gray-200')} />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className={clsx('px-2', isDark ? 'bg-gray-900 text-gray-500' : 'bg-white text-gray-400')}>
                    {t('auth.orPickProfile')}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Mode Switcher */}
          <div className={clsx(
            'flex p-1 rounded-xl border text-xs font-medium',
            isDark ? 'bg-gray-800/80 border-gray-700' : 'bg-gray-100 border-gray-200'
          )}>
            <button
              type="button"
              onClick={() => setMode('officers')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg transition-all',
                mode === 'officers'
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'
              )}
            >
              <ShieldCheck size={14} />
              <span>{t('auth.tabOfficer')}</span>
            </button>
            <button
              type="button"
              onClick={() => setMode('custom')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg transition-all',
                mode === 'custom'
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'
              )}
            >
              <UserCheck size={14} />
              <span>{t('auth.tabCustom')}</span>
            </button>
          </div>

          {/* Tab 1: Predefined Officer Accounts */}
          {mode === 'officers' && (
            <div className="space-y-2.5">
              <p className={clsx('text-xs font-semibold uppercase tracking-wider', isDark ? 'text-gray-400' : 'text-gray-500')}>
                {t('auth.pickOfficer')}
              </p>

              {DEMO_OFFICERS.map((officer) => (
                <button
                  key={officer.id}
                  type="button"
                  onClick={() => loginWithProfile(officer)}
                  className={clsx(
                    'w-full flex items-center gap-3 p-3 rounded-2xl border text-left transition-all duration-150 group cursor-pointer',
                    isDark
                      ? 'bg-gray-800/60 hover:bg-gray-800 border-gray-700 hover:border-blue-500/50'
                      : 'bg-gray-50 hover:bg-blue-50/60 border-gray-200 hover:border-blue-300'
                  )}
                >
                  <img
                    src={officer.picture}
                    alt={officer.name}
                    className="w-11 h-11 rounded-full object-cover border-2 border-blue-500/40 shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className={clsx('font-semibold text-sm truncate', isDark ? 'text-white' : 'text-gray-900')}>
                        {officer.name}
                      </span>
                      <BadgeCheck size={15} className="text-blue-500 shrink-0" />
                    </div>
                    <p className={clsx('text-xs truncate font-medium', isDark ? 'text-blue-400' : 'text-blue-600')}>
                      {officer.role}
                    </p>
                    <p className={clsx('text-[11px] truncate', isDark ? 'text-gray-400' : 'text-gray-500')}>
                      {officer.email}
                    </p>
                  </div>

                  <div className={clsx(
                    'w-8 h-8 rounded-full flex items-center justify-center transition-transform group-hover:translate-x-0.5',
                    isDark ? 'bg-gray-700 text-gray-300 group-hover:bg-blue-600 group-hover:text-white'
                           : 'bg-white text-gray-500 group-hover:bg-blue-600 group-hover:text-white shadow-sm'
                  )}>
                    <ArrowRight size={14} />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Tab 2: Custom Google Account */}
          {mode === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="space-y-3.5">
              <p className={clsx('text-xs', isDark ? 'text-gray-400' : 'text-gray-500')}>
                {t('auth.customIntro')}
              </p>

              <div>
                <label className={clsx('block text-xs font-semibold mb-1', isDark ? 'text-gray-300' : 'text-gray-700')}>
                  {t('auth.fullName')}
                </label>
                <input
                  type="text"
                  placeholder={t('auth.namePlaceholder')}
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  className={clsx(
                    'w-full px-3.5 py-2.5 rounded-xl border text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500',
                    isDark ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500'
                           : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                  )}
                  autoFocus
                />
              </div>

              <div>
                <label className={clsx('block text-xs font-semibold mb-1', isDark ? 'text-gray-300' : 'text-gray-700')}>
                  {t('auth.emailLabel')}
                </label>
                <input
                  type="email"
                  placeholder="hendra.bpbd@gmail.com"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  className={clsx(
                    'w-full px-3.5 py-2.5 rounded-xl border text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500',
                    isDark ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500'
                           : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                  )}
                />
              </div>

              {customError && (
                <p className="text-xs text-red-500 font-medium">
                  {customError}
                </p>
              )}

              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition-all shadow-md active:scale-[0.99]"
              >
                <GoogleIcon size={16} />
                <span>{t('auth.loginThisAccount')}</span>
              </button>
            </form>
          )}

          {/* Compliance & Security Banner */}
          <div className={clsx(
            'p-3 rounded-2xl border text-xs flex items-start gap-2.5',
            isDark ? 'bg-blue-500/10 border-blue-500/20 text-blue-300' : 'bg-blue-50 border-blue-200 text-blue-800'
          )}>
            <ShieldCheck size={16} className="text-blue-500 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>{t('auth.compliance')}</strong> {t('auth.complianceBody')}
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className={clsx(
          'px-6 py-3.5 border-t flex items-center justify-between text-xs',
          isDark ? 'bg-gray-950/50 border-gray-800 text-gray-400' : 'bg-gray-50 border-gray-200 text-gray-500'
        )}>
          <span>SIGAP v0.4.0 • Google Auth</span>
          <button
            type="button"
            onClick={closeAuthModal}
            className={clsx(
              'font-medium transition-colors hover:underline',
              isDark ? 'text-gray-300' : 'text-gray-600'
            )}
          >
            {t('auth.cancel')}
          </button>
        </div>

      </div>
    </div>
  )
}
