/**
 * MapView.jsx v4
 * ──────────────
 * Peta interaktif dengan vulnerability score per kecamatan.
 *
 * Dua mode overlay:
 *   1. LIVE: polygon kecamatan + vulnerability score per kecamatan
 *      - Warna berdasarkan vuln_score (0-100), bukan hanya hazard
 *      - Klik polygon → tampilkan detail kecamatan
 *   2. MOCK (fallback): kotak persegi dari MOCK_FLOOD_ZONES
 */

import { MapContainer, TileLayer, Polygon, Tooltip, ZoomControl, useMap, GeoJSON } from 'react-leaflet'
import { useEffect, useRef, useCallback, useState } from 'react'
import { MOCK_FLOOD_ZONES, CITY_CENTERS } from '../lib/mockData.js'
import { useTheme } from '../lib/ThemeContext.jsx'
import { useFloodPolygons } from '../hooks/useFloodPolygons.js'
import { getVulnerabilityMap } from '../lib/api.js'

const TILES = {
  dark:  { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },
  light: { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },
}

const MOCK_STYLE = {
  high:   { color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.30, weight: 2 },
  medium: { color: '#f97316', fillColor: '#f97316', fillOpacity: 0.22, weight: 1.5 },
  low:    { color: '#eab308', fillColor: '#eab308', fillOpacity: 0.15, weight: 1 },
}

// ── Sub-components ────────────────────────────────────────────────────────────
function FlyToCity({ city }) {
  const map = useMap()
  const cfg = CITY_CENTERS[city]
  useEffect(() => {
    if (cfg) map.flyTo(cfg.center, cfg.zoom, { duration: 1.2, easeLinearity: 0.3 })
  }, [city]) // eslint-disable-line
  return null
}

function ThemeTileLayer() {
  const { theme } = useTheme()
  const tile = TILES[theme] ?? TILES.dark
  return <TileLayer url={tile.url} attribution={tile.attribution} maxZoom={19} />
}

// ── Kecamatan Detail Panel ────────────────────────────────────────────────────
function KecamatanPanel({ kec, isDark, onClose }) {
  if (!kec) return null

  const score = kec.vuln_score ?? 0
  const cat   = kec.vuln_category ?? ''
  const isAwas  = cat.includes('AWAS')
  const isSiaga = cat.includes('SIAGA')

  const bg   = isDark ? '#111827' : '#ffffff'
  const bdr  = isDark ? '#1f2937' : '#f1f5f9'
  const txt  = isDark ? '#f9fafb' : '#111827'
  const sub  = isDark ? '#9ca3af' : '#64748b'

  const scoreColor = score >= 75 ? '#dc2626'
    : score >= 50 ? '#f97316'
    : score >= 25 ? '#eab308'
    : '#22c55e'

  return (
    <div style={{
      position: 'absolute', bottom: 72, left: 12, zIndex: 500, width: 230,
      background: bg, border: `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
      borderRadius: 12, padding: '12px 14px', fontSize: 13,
      boxShadow: '0 8px 24px rgba(0,0,0,0.25)', backdropFilter: 'blur(10px)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <p style={{ fontWeight: 700, color: txt, margin: 0 }}>{kec.name}</p>
          <p style={{ color: sub, fontSize: 11, margin: '2px 0 0', fontStyle: 'italic' }}>{kec.kab}</p>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: sub, fontSize: 16, lineHeight: 1, padding: '0 2px',
        }}>✕</button>
      </div>

      {/* Score gauge */}
      <div style={{
        background: isDark ? '#1f2937' : '#f8fafc',
        borderRadius: 8, padding: '8px 10px', marginBottom: 10,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ color: sub, fontSize: 11 }}>Vulnerability Score</span>
          <span style={{ fontWeight: 800, fontSize: 18, color: scoreColor }}>{score}</span>
        </div>
        {/* Progress bar */}
        <div style={{ height: 5, background: isDark ? '#374151' : '#e2e8f0', borderRadius: 99 }}>
          <div style={{ height: '100%', width: `${score}%`, background: scoreColor, borderRadius: 99, transition: 'width 0.6s ease' }} />
        </div>
        <p style={{ color: scoreColor, fontWeight: 600, fontSize: 12, margin: '6px 0 0', textAlign: 'right' }}>{cat}</p>
      </div>

      {/* Detail rows */}
      {[
        { label: 'Indeks Bahaya BNPB', value: kec.hazard?.toFixed(3) ?? '-' },
        { label: 'Kelas Bahaya',        value: kec.risk?.replace('_', ' ') ?? '-' },
        { label: 'Est. Populasi',       value: kec.population_est ? `${kec.population_est.toLocaleString('id-ID')} jiwa` : '-' },
      ].map(({ label, value }) => (
        <div key={label} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          paddingBottom: 5, marginBottom: 5,
          borderBottom: `1px solid ${isDark ? '#1f2937' : '#f1f5f9'}`,
        }}>
          <span style={{ color: sub, fontSize: 11 }}>{label}</span>
          <span style={{ color: txt, fontSize: 12, fontWeight: 500 }}>{value}</span>
        </div>
      ))}

      {/* Alert banner */}
      {(isAwas || isSiaga) && (
        <div style={{
          background: isAwas ? 'rgba(220,38,38,0.12)' : 'rgba(249,115,22,0.12)',
          border: `1px solid ${isAwas ? 'rgba(220,38,38,0.3)' : 'rgba(249,115,22,0.3)'}`,
          borderRadius: 6, padding: '5px 8px', fontSize: 11,
          color: isAwas ? '#ef4444' : '#f97316', marginTop: 4,
        }}>
          {isAwas ? '🚨 Butuh perhatian segera' : '⚠️ Pantau secara aktif'}
        </div>
      )}

      <p style={{ color: sub, fontSize: 10, margin: '8px 0 0', textAlign: 'center' }}>
        Klik kecamatan lain untuk membandingkan
      </p>
    </div>
  )
}

// ── Live GeoJSON Layer (vulnerability-colored) ────────────────────────────────
function LiveVulnLayer({ geojson, isDark, onKecamatanClick }) {
  const geoJsonRef = useRef(null)

  const styleFeature = useCallback((feature) => {
    // Gunakan vuln_color kalau ada, fallback ke color (hazard-based)
    const color = feature?.properties?.vuln_color ?? feature?.properties?.color ?? '#f97316'
    return { color, fillColor: color, fillOpacity: 0.35, weight: 1.5, opacity: 0.9 }
  }, [])

  const onEachFeature = useCallback((feature, layer) => {
    const p = feature.properties

    // Tooltip hover — tampilkan score
    const tooltipEl = document.createElement('div')
    const bg  = isDark ? '#1f2937' : '#fff'
    const fg  = isDark ? '#f3f4f6' : '#111'
    const bdr = isDark ? '#374151' : '#e5e7eb'
    tooltipEl.style.cssText = `background:${bg};color:${fg};border:1px solid ${bdr};border-radius:8px;padding:8px 10px;min-width:160px;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.3)`

    const scoreColor = (p.vuln_score ?? 0) >= 75 ? '#dc2626'
      : (p.vuln_score ?? 0) >= 50 ? '#f97316'
      : (p.vuln_score ?? 0) >= 25 ? '#ca8a04'
      : '#16a34a'

    tooltipEl.innerHTML = `
      <p style="font-weight:700;margin:0 0 4px">${p.name}</p>
      <p style="color:${scoreColor};font-weight:600;margin:0 0 2px">${p.vuln_category ?? ''} &nbsp; <b>${p.vuln_score ?? '-'}</b>/100</p>
      <p style="opacity:.65;font-size:11px;margin:0">Bahaya BNPB: ${p.hazard?.toFixed(3) ?? 'N/A'} &bull; Klik untuk detail</p>
    `
    layer.bindTooltip(tooltipEl, { sticky: true, className: 'inarisk-tooltip' })

    layer.on({
      mouseover: (e) => { e.target.setStyle({ fillOpacity: 0.65, weight: 2.5 }); e.target.bringToFront() },
      mouseout:  (e) => { if (geoJsonRef.current) geoJsonRef.current.resetStyle(e.target) },
      click:     () => { onKecamatanClick(p) },
    })
  }, [isDark, onKecamatanClick])

  if (!geojson) return null

  return (
    <GeoJSON
      ref={geoJsonRef}
      key={`${geojson.city}-${geojson._generated_at}`}
      data={geojson}
      style={styleFeature}
      onEachFeature={onEachFeature}
    />
  )
}

// ── Mock Overlay (fallback) ───────────────────────────────────────────────────
function MockFloodLayer({ city, isDark }) {
  const zones = MOCK_FLOOD_ZONES[city] ?? []
  return (
    <>
      {zones.map(zone => (
        <Polygon
          key={zone.id}
          positions={zone.coords}
          pathOptions={MOCK_STYLE[zone.risk] ?? MOCK_STYLE.low}
          eventHandlers={{
            mouseover: e => e.target.setStyle({ ...MOCK_STYLE[zone.risk], fillOpacity: 0.55 }),
            mouseout:  e => e.target.setStyle(MOCK_STYLE[zone.risk]),
          }}
        >
          <Tooltip sticky>
            <div style={{
              background: isDark ? '#1f2937' : '#fff', color: isDark ? '#f3f4f6' : '#111',
              border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
              borderRadius: 8, padding: '8px 10px', minWidth: 160, fontSize: 13,
            }}>
              <p style={{ fontWeight: 700, marginBottom: 4 }}>{zone.name}</p>
              <p style={{ color: '#f97316', marginBottom: 4 }}>
                {zone.risk === 'high' ? '🔴 Risiko Tinggi' : zone.risk === 'medium' ? '🟠 Risiko Sedang' : '🟡 Risiko Rendah'}
              </p>
              <p style={{ opacity: 0.75, fontSize: 12 }}>Est. {zone.pop_est?.toLocaleString('id-ID')} jiwa</p>
              <p style={{ opacity: 0.4, fontSize: 10, marginTop: 4 }}>⚠️ Mock data</p>
            </div>
          </Tooltip>
        </Polygon>
      ))}
    </>
  )
}

// ── Legend ────────────────────────────────────────────────────────────────────
function MapLegend({ isDark, isLive }) {
  const bg  = isDark ? 'rgba(17,24,39,0.92)' : 'rgba(255,255,255,0.92)'
  const bdr = isDark ? '#374151' : '#e2e8f0'
  const txt = isDark ? '#d1d5db' : '#374151'
  const sub = isDark ? '#6b7280' : '#94a3b8'

  const levels = isLive ? [
    { color: '#dc2626', label: '🔴 AWAS (75-100)' },
    { color: '#f97316', label: '🟠 SIAGA (50-75)' },
    { color: '#eab308', label: '🟡 WASPADA (25-50)' },
    { color: '#22c55e', label: '🟢 NORMAL (0-25)' },
  ] : [
    { color: '#ef4444', label: '🔴 Risiko Tinggi' },
    { color: '#f97316', label: '🟠 Risiko Sedang' },
    { color: '#eab308', label: '🟡 Risiko Rendah' },
  ]

  return (
    <div style={{
      position: 'absolute', bottom: 20, left: 12, zIndex: 400,
      background: bg, border: `1px solid ${bdr}`, borderRadius: 12,
      padding: '10px 14px', fontSize: 12, backdropFilter: 'blur(8px)',
      boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
    }}>
      <p style={{ color: txt, fontWeight: 600, marginBottom: 8 }}>
        {isLive ? 'Vulnerability Score per Kecamatan' : 'Zona Banjir (Estimasi)'}
      </p>
      {levels.map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: color, opacity: 0.8 }} />
          <span style={{ color: txt }}>{label}</span>
        </div>
      ))}
      <div style={{ borderTop: `1px solid ${bdr}`, paddingTop: 6, marginTop: 4, color: sub }}>
        {isLive ? 'Klik kecamatan untuk detail' : '⚠️ Bukan data riil'}
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function MapView({ selectedCity }) {
  const { theme }   = useTheme()
  const isDark      = theme === 'dark'
  const cityData    = CITY_CENTERS[selectedCity] ?? CITY_CENTERS.semarang

  // State: polygon vulnerability map (per-kecamatan)
  const [vulnMap,      setVulnMap]      = useState(null)
  const [vulnLoading,  setVulnLoading]  = useState(false)
  const [selectedKec,  setSelectedKec]  = useState(null)

  // Fallback: flood polygon biasa (hazard-colored)
  const { polygons: floodPolygons, loading: fallbackLoading } = useFloodPolygons(selectedCity)

  // Fetch vulnerability map per kota
  useEffect(() => {
    if (!selectedCity) return
    setSelectedKec(null)
    setVulnMap(null)
    setVulnLoading(true)

    getVulnerabilityMap(selectedCity)
      .then(data => { setVulnMap(data); setVulnLoading(false) })
      .catch(() => { setVulnLoading(false) })
  }, [selectedCity])

  // Gunakan vulnMap kalau ada, fallback ke floodPolygons, fallback ke mock
  const activeGeojson  = vulnMap ?? floodPolygons
  const hasLive        = activeGeojson && activeGeojson.features?.length > 0
  const isLoading      = vulnLoading || fallbackLoading
  const isVulnMode     = !!vulnMap

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 420 }}>
      <MapContainer
        center={cityData.center}
        zoom={cityData.zoom}
        zoomControl={false}
        style={{
          width: '100%', height: '100%', minHeight: 420,
          borderRadius: '0.75rem',
          background: isDark ? '#111827' : '#e2e8f0',
        }}
      >
        <ThemeTileLayer />
        <FlyToCity city={selectedCity} />
        <ZoomControl position="bottomright" />

        {hasLive
          ? <LiveVulnLayer
              geojson={activeGeojson}
              isDark={isDark}
              onKecamatanClick={setSelectedKec}
            />
          : <MockFloodLayer city={selectedCity} isDark={isDark} />
        }
      </MapContainer>

      {/* Legend */}
      <MapLegend isDark={isDark} isLive={hasLive} isVulnMode={isVulnMode} />

      {/* Kecamatan detail panel (on click) */}
      {selectedKec && (
        <KecamatanPanel
          kec={selectedKec}
          isDark={isDark}
          onClose={() => setSelectedKec(null)}
        />
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 400, background: isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
          border: `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
          borderRadius: 8, padding: '6px 14px', fontSize: 12,
          color: isDark ? '#93c5fd' : '#3b82f6', backdropFilter: 'blur(8px)',
        }}>
          ⟳ {isVulnMode ? 'Memuat vulnerability map...' : 'Memuat polygon InaRisk...'}
        </div>
      )}

      {/* City label + feature count */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 400,
        background: isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
        border: `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
        borderRadius: 8, padding: '6px 12px', fontSize: 13, fontWeight: 600,
        color: isDark ? '#f3f4f6' : '#1e293b', backdropFilter: 'blur(8px)',
      }}>
        📍 {selectedCity.charAt(0).toUpperCase() + selectedCity.slice(1)}
        {hasLive && (
          <span style={{ marginLeft: 6, fontSize: 11, color: isDark ? '#6b7280' : '#94a3b8', fontWeight: 400 }}>
            {activeGeojson.features.length} kecamatan
            {isVulnMode && <span style={{ marginLeft: 4, color: isDark ? '#60a5fa' : '#3b82f6' }}>● vuln</span>}
          </span>
        )}
      </div>
    </div>
  )
}
