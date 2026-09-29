/**
 * hooks/useAnalysis.js
 * ────────────────────
 * Custom hook — orkestrasi semua data fetching untuk satu kota.
 * v2: Tambah fetchWeather()
 */

import { useState, useEffect, useCallback } from 'react'
import { getAlerts, getVulnerability, getNarasi, getWeather } from '../lib/api.js'

export function useAnalysis(city) {
  const [alerts,        setAlerts]        = useState(null)
  const [weather,       setWeather]       = useState(null)
  const [vulnerability, setVulnerability] = useState(null)
  const [narasi,        setNarasi]        = useState(null)
  const [loading, setLoading] = useState({
    alerts: false, weather: false, vulnerability: false, narasi: false,
  })
  const [errors,      setErrors]      = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAlerts = useCallback(async () => {
    setLoading(p => ({ ...p, alerts: true }))
    try {
      setAlerts(await getAlerts(true))
      setErrors(p => ({ ...p, alerts: null }))
    } catch (e) {
      setErrors(p => ({ ...p, alerts: e.message }))
    } finally {
      setLoading(p => ({ ...p, alerts: false }))
    }
  }, [])

  const fetchWeather = useCallback(async (c) => {
    setLoading(p => ({ ...p, weather: true }))
    try {
      setWeather(await getWeather(c))
      setErrors(p => ({ ...p, weather: null }))
    } catch (e) {
      setErrors(p => ({ ...p, weather: e.message }))
    } finally {
      setLoading(p => ({ ...p, weather: false }))
    }
  }, [])

  const fetchVulnerability = useCallback(async (c) => {
    setLoading(p => ({ ...p, vulnerability: true }))
    try {
      setVulnerability(await getVulnerability(c))
      setErrors(p => ({ ...p, vulnerability: null }))
    } catch (e) {
      setErrors(p => ({ ...p, vulnerability: e.message }))
    } finally {
      setLoading(p => ({ ...p, vulnerability: false }))
    }
  }, [])

  const fetchNarasi = useCallback(async (c) => {
    setLoading(p => ({ ...p, narasi: true }))
    try {
      setNarasi(await getNarasi(c))
      setErrors(p => ({ ...p, narasi: null }))
    } catch (e) {
      setErrors(p => ({ ...p, narasi: e.message }))
    } finally {
      setLoading(p => ({ ...p, narasi: false }))
    }
  }, [])

  const refresh = useCallback(async () => {
    if (!city) return
    await Promise.all([
      fetchAlerts(),
      fetchWeather(city),
      fetchVulnerability(city),
      fetchNarasi(city),
    ])
    setLastUpdated(new Date())
  }, [city, fetchAlerts, fetchWeather, fetchVulnerability, fetchNarasi])

  useEffect(() => { refresh() }, [city])

  // Auto-refresh setiap 5 menit
  useEffect(() => {
    const iv = setInterval(refresh, 5 * 60 * 1000)
    return () => clearInterval(iv)
  }, [refresh])

  return {
    alerts,
    weather,
    vulnerability,
    narasi,
    loading,
    isLoading: Object.values(loading).some(Boolean),
    errors,
    lastUpdated,
    refresh,
  }
}
