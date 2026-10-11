import { useEffect, useMemo, useRef, useState } from 'react'
import { RefreshCw, Wifi, WifiOff, Clock, Sun, Moon, Search } from 'lucide-react'
import clsx from 'clsx'
import { useTheme } from '../lib/ThemeContext.jsx'

export default function Header({
  selectedCity, cities, onCityChange,
  onRefresh, isLoading, lastUpdated, isLive
}) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const boxRef = useRef(null)
  const selected = cities.find(city => city.id === selectedCity)

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase()
    const source = q
      ? cities.filter(city =>
          city.label?.toLowerCase().includes(q) ||
          city.province?.toLowerCase().includes(q) ||
          city.id?.includes(q)
        )
      : cities
    return source.slice(0, 30)
  }, [cities, query])

  useEffect(() => {
    const onDoc = (event) => {
      if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const pick = (city) => {
    onCityChange(city.id)
    setQuery('')
    setOpen(false)
  }

  return (
    <header className={clsx(
      'flex items-center justify-between px-5 py-3 shrink-0 border-b',
      isDark
        ? 'bg-gray-900 border-gray-800'
        : 'bg-white border-gray-200'
    )}>
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <span className="text-2xl">🌊</span>
        <div>
          <h1 className={clsx('font-bold text-lg leading-none',
            isDark ? 'text-white' : 'text-gray-900'
          )}>SIGAP</h1>
          <p className={clsx('text-xs leading-none mt-0.5',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>
            Sistem Penanggulangan Banjir
          </p>
        </div>
      </div>

      {/* City selector */}
      <div className="flex items-center gap-2" ref={boxRef}>
        <label className={clsx('text-sm', isDark ? 'text-gray-400' : 'text-gray-600')}>
          Kota:
        </label>
        <div className="relative">
          <div className={clsx(
            'flex items-center gap-1.5 border rounded-lg px-2.5 py-1.5',
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-300'
          )}>
            <Search size={13} className={isDark ? 'text-gray-500' : 'text-gray-400'} />
            <input
              value={open ? query : (selected ? `${selected.label}` : selectedCity)}
              placeholder="Cari kab/kota"
              onFocus={() => { setOpen(true); setQuery('') }}
              onChange={e => { setQuery(e.target.value); setOpen(true) }}
              className={clsx(
                'bg-transparent text-sm w-52 focus:outline-none',
                isDark ? 'text-white placeholder:text-gray-500' : 'text-gray-900 placeholder:text-gray-400'
              )}
            />
          </div>
          {open && (
            <div className={clsx(
              'absolute z-50 mt-1 w-72 max-h-72 overflow-y-auto rounded-lg border shadow-lg',
              isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
            )}>
              {matches.length === 0 && (
                <p className={clsx('px-3 py-2 text-xs', isDark ? 'text-gray-500' : 'text-gray-400')}>
                  Tidak ada kota yang cocok
                </p>
              )}
              {matches.map(city => (
                <button
                  key={city.id}
                  type="button"
                  onClick={() => pick(city)}
                  className={clsx(
                    'block w-full text-left px-3 py-2 text-sm',
                    city.id === selectedCity
                      ? isDark ? 'bg-blue-500/20 text-blue-200' : 'bg-blue-50 text-blue-700'
                      : isDark ? 'text-gray-200 hover:bg-gray-800' : 'text-gray-800 hover:bg-gray-50'
                  )}
                >
                  <span className="block leading-tight">{city.label}</span>
                  <span className={clsx('block text-xs', isDark ? 'text-gray-500' : 'text-gray-400')}>
                    {city.province} · {city.id}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-3">
        {/* Live indicator */}
        <div className="flex items-center gap-1.5">
          {isLive
            ? <Wifi size={13} className="text-green-500" />
            : <WifiOff size={13} className="text-yellow-500" />
          }
          <span className={clsx('text-xs',
            isLive ? 'text-green-500' : 'text-yellow-500'
          )}>
            {isLive ? 'Live' : 'Mock'}
          </span>
        </div>

        {/* Last updated */}
        {lastUpdated && (
          <div className={clsx('flex items-center gap-1 text-xs',
            isDark ? 'text-gray-500' : 'text-gray-400'
          )}>
            <Clock size={11} />
            {lastUpdated.toLocaleTimeString('id-ID', {
              hour: '2-digit', minute: '2-digit', second: '2-digit'
            })}
          </div>
        )}

        {/* Dark/Light toggle */}
        <button
          onClick={toggleTheme}
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className={clsx(
            'p-1.5 rounded-lg transition-colors',
            isDark
              ? 'bg-gray-800 hover:bg-gray-700 text-yellow-400'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
          )}
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-white',
            'transition-colors disabled:opacity-50',
            'bg-blue-600 hover:bg-blue-500'
          )}
        >
          <RefreshCw size={13} className={clsx(isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>
    </header>
  )
}
