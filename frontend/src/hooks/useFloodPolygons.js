/**
 * hooks/useFloodPolygons.js
 * ─────────────────────────
 * Fetch polygon batas kecamatan + nilai bahaya dari InaRisk BNPB.
 * Dipakai oleh MapView untuk menggantikan kotak mock hardcoded.
 *
 * - Pertama kali fetch: bisa lambat (~20-30s, InaRisk generate on-demand)
 * - Subsequent: sangat cepat (dari cache backend 7 hari)
 * - Fallback: kalau gagal, MapView pakai MOCK_FLOOD_ZONES
 * - Retry: otomatis coba ulang jika response kosong (polygon belum tersedia)
 */

import { useState, useEffect } from 'react'
import { getFloodPolygons } from '../lib/api.js'

export function useFloodPolygons(city) {
  const [polygons,  setPolygons]  = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    if (!city) return

    let cancelled = false
    let retryCount = 0
    const MAX_RETRIES = 4
    const RETRY_INTERVAL = 5000 // 5 detik

    setLoading(true)
    setError(null)
    setPolygons(null)

    const fetchPolygons = () => {
      getFloodPolygons(city)
        .then(data => {
          if (cancelled) return
          if (data && data.features && data.features.length > 0) {
            setPolygons(data)
            setLoading(false)
          } else if (retryCount < MAX_RETRIES) {
            // Polygon belum siap di backend, coba lagi
            retryCount++
            setTimeout(fetchPolygons, RETRY_INTERVAL)
          } else {
            setLoading(false)
          }
        })
        .catch(err => {
          if (!cancelled) {
            setError(err.message)
            setLoading(false)
          }
        })
    }

    fetchPolygons()
    return () => { cancelled = true }
  }, [city])

  return { polygons, loading, error }
}
