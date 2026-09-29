import { RefreshCw, Wifi, WifiOff, Clock, Sun, Moon } from 'lucide-react'
import clsx from 'clsx'
import { useTheme } from '../lib/ThemeContext.jsx'

export default function Header({
  selectedCity, cities, onCityChange,
  onRefresh, isLoading, lastUpdated, isLive
}) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

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
      <div className="flex items-center gap-2">
        <label className={clsx('text-sm', isDark ? 'text-gray-400' : 'text-gray-600')}>
          Kota:
        </label>
        <select
          value={selectedCity}
          onChange={e => onCityChange(e.target.value)}
          className={clsx(
            'border rounded-lg px-3 py-1.5 text-sm cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-blue-500',
            isDark
              ? 'bg-gray-800 text-white border-gray-700'
              : 'bg-gray-50 text-gray-900 border-gray-300'
          )}
        >
          {cities.map(c => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
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
