/**
 * hooks/useFloodReports.js
 * ─────────────────────────
 * Custom hook untuk flood report lapangan.
 * Menghandle: submit, fetch rivers, fetch reports, clear.
 *
 * Ketika submitReport berhasil → callback onSuccess dipanggil
 * sehingga parent bisa trigger refresh vulnerability score.
 */

import { useState, useEffect, useCallback } from 'react'
import { submitFloodReport, getFloodReports, getFloodRivers, clearFloodReports } from '../lib/api.js'

export function useFloodReports(city, onSuccess) {
  const [rivers,  setRivers]  = useState([])
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const fetchRivers = useCallback(async (c) => {
    try {
      const data = await getFloodRivers(c)
      setRivers(data?.rivers ?? [])
    } catch { setRivers([]) }
  }, [])

  const fetchReports = useCallback(async (c) => {
    try {
      const data = await getFloodReports(c)
      setReports(data?.reports ?? [])
    } catch { setReports([]) }
  }, [])

  // Fetch ulang ketika city berubah
  useEffect(() => {
    if (!city) return
    fetchRivers(city)
    fetchReports(city)
  }, [city, fetchRivers, fetchReports])

  const submit = useCallback(async (formData) => {
    setLoading(true)
    setError(null)
    try {
      await submitFloodReport(formData)
      await fetchReports(city)  // refresh list setelah submit
      onSuccess?.()              // trigger refresh vulnerability score
    } catch (e) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [city, fetchReports, onSuccess])

  const clear = useCallback(async () => {
    try {
      await clearFloodReports(city)
      setReports([])
      onSuccess?.()
    } catch (e) {
      setError(e.message)
    }
  }, [city, onSuccess])

  return { rivers, reports, loading, error, submit, clear }
}
