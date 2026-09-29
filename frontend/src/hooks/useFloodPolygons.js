/**
 * hooks/useFloodPolygons.js
 * ─────────────────────────
 * Fetch polygon batas kecamatan + nilai bahaya dari InaRisk BNPB.
 * Dipakai oleh MapView untuk menggantikan kotak mock hardcoded.
 *
 * - Pertama kali fetch: bisa lambat (~20-30s, InaRisk generate on-demand)
 * - Subsequent: sangat cepat (dari cache backend 7 hari)
 * - Fallback: kalau gagal, MapView pakai MOCK_FLOOD_ZONES
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
    setLoading(true)
    setError(null)
    setPolygons(null)

    getFloodPolygons(city)
      .then(data => {
        if (!cancelled) {
          setPolygons(data)
          setLoading(false)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [city])

  return { polygons, loading, error }
}
