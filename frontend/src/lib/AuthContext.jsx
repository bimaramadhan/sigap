/**
 * AuthContext.jsx
 * ───────────────
 * Context autentikasi petugas BPBD menggunakan Google Sign-In.
 *
 * Fitur:
 * 1. Google Identity Services (GIS) native jika VITE_GOOGLE_CLIENT_ID tersedia.
 * 2. Instant Demo Google Officer accounts untuk evaluasi dan testing cepat tanpa blocking.
 * 3. Persistensi session login di localStorage ('sigap_officer_user').
 * 4. Hook useAuth() untuk akses status login, profil petugas, dan kontrol modal auth.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const STORAGE_KEY = 'sigap_officer_user'
// Masa aktif sesi: 24 jam (sesuai siklus piket operasional Pusdalops/TRC BPBD)
const SESSION_TTL_MS = 24 * 60 * 60 * 1000

// Helper: Memeriksa apakah session data masih valid dan belum expired
function getValidStoredUser() {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || !parsed.loginAt) {
      localStorage.removeItem(STORAGE_KEY)
      return null
    }

    const elapsed = Date.now() - new Date(parsed.loginAt).getTime()
    if (elapsed > SESSION_TTL_MS) {
      console.warn('Sesi login petugas telah kedaluwarsa (> 24 jam). Menghapus sesi.')
      localStorage.removeItem(STORAGE_KEY)
      return null
    }

    return parsed
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

// Demo accounts for rapid testing & evaluation
export const DEMO_OFFICERS = [
  {
    id: 'bpbd-off-001',
    name: 'Budi Santoso, S.T.',
    email: 'budi.santoso@bpbd.go.id',
    role: 'Koordinator Lapangan BPBD',
    agency: 'BPBD Kota Semarang / Jawa Tengah',
    badgeNumber: 'BPBD-TRC-3374',
    picture: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    verified: true,
  },
  {
    id: 'bpbd-off-002',
    name: 'Siti Rahmawati, M.Sc.',
    email: 'siti.rahmawati@bpbd.go.id',
    role: 'Operator Pusdalops BPBD',
    agency: 'Pusdalops PB BPBD',
    badgeNumber: 'BPBD-OPS-3374',
    picture: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80',
    verified: true,
  },
  {
    id: 'bpbd-off-003',
    name: 'Ahmad Fauzi',
    email: 'ahmad.fauzi@bpbd.go.id',
    role: 'Komandan Tim Reaksi Cepat (TRC)',
    agency: 'TRC Tanggap Darurat BPBD',
    badgeNumber: 'BPBD-TRC-082',
    picture: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    verified: true,
  },
]

function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getValidStoredUser())

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false)

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

  // Sinkronisasi sesi antar-tab browser (Cross-Tab Session Sync)
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === STORAGE_KEY) {
        setUser(getValidStoredUser())
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  // Validasi sesi saat tab kembali aktif (Window Visibility Check)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const valid = getValidStoredUser()
        setUser(valid)
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [])

  // Load Google Identity Services SDK dynamically
  useEffect(() => {
    if (typeof window === 'undefined') return

    if (window.google?.accounts?.id) {
      setIsGoogleLoaded(true)
      return
    }

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => {
      setIsGoogleLoaded(true)
    }
    script.onerror = () => {
      console.warn('Google Identity Services script failed to load, demo mode remains active.')
    }
    document.head.appendChild(script)

    return () => {
      // Don't remove script to avoid reloads
    }
  }, [])

  // Initialize GIS if client ID is provided
  useEffect(() => {
    if (!isGoogleLoaded || !googleClientId || typeof window.google === 'undefined') return

    try {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredentialResponse,
        auto_select: false,
      })
    } catch (err) {
      console.warn('GSI initialize error:', err)
    }
  }, [isGoogleLoaded, googleClientId])

  // Helper untuk menyimpan sesi ke localStorage dengan metadata TTL lengkap
  const saveSession = useCallback((profileData) => {
    const sessionData = {
      ...profileData,
      verified: true,
      isGoogle: true,
      loginAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + SESSION_TTL_MS).toISOString(),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionData))
    return sessionData
  }, [])

  const handleGoogleCredentialResponse = useCallback((response) => {
    if (!response?.credential) return
    const payload = parseJwt(response.credential)
    if (!payload) return

    const officerUser = saveSession({
      id: payload.sub || `google-${Date.now()}`,
      name: payload.name || 'Petugas BPBD',
      email: payload.email || '',
      picture: payload.picture || '',
      role: 'Petugas Lapangan BPBD Terverifikasi',
      agency: 'BPBD (Google Verified)',
    })

    setUser(officerUser)
    setIsAuthModalOpen(false)
  }, [saveSession])

  const loginWithProfile = useCallback((profile) => {
    const officerUser = saveSession(profile)
    setUser(officerUser)
    setIsAuthModalOpen(false)
  }, [saveSession])

  const loginWithCustomGoogle = useCallback(({ name, email }) => {
    const customUser = saveSession({
      id: `custom-google-${Date.now()}`,
      name: name?.trim() || 'Petugas BPBD',
      email: email?.trim() || 'petugas.bpbd@gmail.com',
      role: 'Petugas Lapangan BPBD',
      agency: 'BPBD Terverifikasi',
      picture: `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name || 'BPBD')}&backgroundColor=1d4ed8,2563eb`,
    })
    setUser(customUser)
    setIsAuthModalOpen(false)
  }, [saveSession])

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
    if (window.google?.accounts?.id) {
      try {
        window.google.accounts.id.disableAutoSelect()
      } catch {}
    }
  }, [])

  const openAuthModal = useCallback(() => setIsAuthModalOpen(true), [])
  const closeAuthModal = useCallback(() => setIsAuthModalOpen(false), [])

  const loginWithGoogle = useCallback(() => {
    if (googleClientId && window.google?.accounts?.id) {
      try {
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Fallback to modal if one-tap is suppressed
            setIsAuthModalOpen(true)
          }
        })
        return
      } catch {
        setIsAuthModalOpen(true)
      }
    }
    setIsAuthModalOpen(true)
  }, [googleClientId])

  const value = {
    user,
    isAuthenticated: !!user,
    isAuthModalOpen,
    isGoogleLoaded,
    hasGoogleClientId: !!googleClientId,
    loginWithGoogle,
    loginWithProfile,
    loginWithCustomGoogle,
    handleGoogleCredentialResponse,
    logout,
    openAuthModal,
    closeAuthModal,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
