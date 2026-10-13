import { RefreshCw, Wifi, WifiOff, Clock, Sun, Moon, Map, FileText } from 'lucide-react'
import clsx from 'clsx'
import { useTheme } from '../lib/ThemeContext.jsx'

export default function Header({
  selectedCity, cities, onCityChange,
  onRefresh, isLoading, lastUpdated, isLive,
  currentPath = '/', onNavigate = () => {},
}) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <header className={clsx(
      'flex items-center justify-between px-4 md:px-5 py-3 shrink-0 border-b gap-3 flex-wrap sm:flex-nowrap',
      isDark
        ? 'bg-gray-900 border-gray-800'
        : 'bg-white border-gray-200'
    )}>
      {/* Left section: Logo & Nav */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div
          onClick={() => onNavigate('/')}
          className="flex items-center gap-2.5 cursor-pointer select-none"
          title="Ke Dashboard"
        >
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

        {/* Navigation Tabs */}
        <nav className={clsx(
          'flex items-center gap-1 p-1 rounded-xl border text-xs',
          isDark ? 'bg-gray-800/80 border-gray-700/80' : 'bg-gray-100 border-gray-200'
        )}>
          <button
            type="button"
            onClick={() => onNavigate('/')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all',
              currentPath === '/'
                ? 'bg-blue-600 text-white shadow-sm'
                : isDark
                  ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/60'
            )}
          >
            <Map size={13} />
            <span className="hidden sm:inline">Dashboard</span>
            <span className="sm:hidden">Peta</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('/report')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all',
              currentPath === '/report'
                ? 'bg-blue-600 text-white shadow-sm'
                : isDark
                  ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/60'
            )}
          >
            <FileText size={13} />
            <span className="hidden sm:inline">Laporan & Briefing</span>
            <span className="sm:hidden">Laporan</span>
          </button>
        </nav>
      </div>

      {/* Middle section: City selector */}
      <div className="flex items-center gap-2">
        <label className={clsx('text-sm hidden sm:inline', isDark ? 'text-gray-400' : 'text-gray-600')}>
          Kota:
        </label>
        <select
          value={selectedCity}
          onChange={e => onCityChange(e.target.value)}
          className={clsx(
            'border rounded-lg px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm cursor-pointer',
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
