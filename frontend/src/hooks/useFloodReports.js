/**
 * hooks/useFloodReports.js
 * ─────────────────────────
 * Custom hook untuk flood report lapangan.
 * Menghandle: submit, fetch villages, fetch reports, clear.
 *
 * Ketika submitReport berhasil → callback onSuccess dipanggil
 * sehingga parent bisa trigger refresh vulnerability score.
 */

import { useState, useEffect, useCallback } from 'react'
import { submitFloodReport, getFloodReports, getFloodVillages, clearFloodReports } from '../lib/api.js'

export function useFloodReports(city, onSuccess) {
  const [villages,         setVillages]         = useState([])
  const [reports,          setReports]          = useState([])
  const [kecamatanBoosts, setKecamatanBoosts]   = useState({})
  const [loading,          setLoading]          = useState(false)
  const [error,            setError]            = useState(null)

  const fetchVillages = useCallback(async (c) => {
    try {
      const data = await getFloodVillages(c)
      setVillages(data?.groups ?? [])
    } catch { setVillages([]) }
  }, [])

  const fetchReports = useCallback(async (c) => {
    try {
      const data = await getFloodReports(c)
      setReports(data?.reports ?? [])
      setKecamatanBoosts(data?.kecamatan_boosts ?? {})
    } catch {
      setReports([])
      setKecamatanBoosts({})
    }
  }, [])

  useEffect(() => {
    if (!city) return
    fetchVillages(city)
    fetchReports(city)
  }, [city, fetchVillages, fetchReports])

  const submit = useCallback(async (formData) => {
    setLoading(true)
    setError(null)
    try {
      await submitFloodReport(formData)
      await fetchReports(city)
      onSuccess?.()
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
      setKecamatanBoosts({})
      onSuccess?.()
    } catch (e) {
      setError(e.message)
    }
  }, [city, onSuccess])

  return { villages, reports, kecamatanBoosts, loading, error, submit, clear }
}
