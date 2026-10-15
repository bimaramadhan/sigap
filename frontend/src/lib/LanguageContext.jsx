/**
 * LanguageContext.jsx
 * ───────────────────
 * Context untuk bahasa UI: Indonesia ('id') / English ('en').
 * Mirror pola ThemeContext — preference disimpan di localStorage.
 *
 * Pakai:
 *   const { lang, toggleLang, t, fmtNum, fmtTime } = useLanguage()
 *   t('header.refresh')      → "Refresh" / "Refresh"
 *   t('status.affected', { n: 1200 })  → interpolasi {n}
 *   fmtNum(1200)             → "1.200" (id) / "1,200" (en)
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { STRINGS } from './i18n.js'

const LanguageContext = createContext({
  lang: 'id',
  toggleLang: () => {},
  setLang: () => {},
  t: (k) => k,
  fmtNum: (n) => String(n),
  fmtTime: (d) => '',
  fmtDateTime: (d) => '',
})

function resolve(dict, key) {
  // key bertitik: "header.refresh" → dict.header.refresh
  return key.split('.').reduce((acc, part) => (acc && acc[part] != null ? acc[part] : undefined), dict)
}

function interpolate(str, params) {
  if (!params || typeof str !== 'string') return str
  return str.replace(/\{(\w+)\}/g, (m, k) => (params[k] != null ? params[k] : m))
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('sigap-lang') ?? 'id')

  useEffect(() => {
    localStorage.setItem('sigap-lang', lang)
    document.documentElement.setAttribute('lang', lang)
  }, [lang])

  const value = useMemo(() => {
    const locale = lang === 'en' ? 'en-US' : 'id-ID'

    const t = (key, params) => {
      const primary  = resolve(STRINGS[lang], key)
      const fallback = resolve(STRINGS.id, key)   // fallback ke ID kalau key hilang
      const str = primary != null ? primary : (fallback != null ? fallback : key)
      return interpolate(str, params)
    }

    const fmtNum = (n) => {
      if (n == null || isNaN(n)) return '-'
      return Number(n).toLocaleString(locale)
    }

    const fmtTime = (d) => {
      if (!d) return ''
      const date = d instanceof Date ? d : new Date(d)
      return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
    }

    const fmtDateTime = (d) => {
      if (!d) return ''
      const date = d instanceof Date ? d : new Date(d)
      return date.toLocaleString(locale)
    }

    return {
      lang,
      setLang,
      toggleLang: () => setLang((l) => (l === 'id' ? 'en' : 'id')),
      t,
      fmtNum,
      fmtTime,
      fmtDateTime,
      locale,
    }
  }, [lang])

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => useContext(LanguageContext)
