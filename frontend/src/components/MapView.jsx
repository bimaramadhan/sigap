/**
 * MapView.jsx v3
 * ──────────────
 * Peta interaktif dengan flood zone overlay.
 *
 * Dua mode overlay:
 *   1. LIVE (via InaRisk API): polygon kecamatan asli + nilai hazard nyata
 *      - Menggunakan react-leaflet GeoJSON component
 *      - Warna berdasarkan INDEKS_BAHAYA_BANJIR dari BNPB
 *   2. MOCK (fallback): kotak persegi dari MOCK_FLOOD_ZONES
 *      - Dipakai saat API tidak tersedia atau VITE_USE_MOCK=true
 */

import { MapContainer, TileLayer, Polygon, Tooltip, ZoomControl, useMap, GeoJSON } from 'react-leaflet'
import { useEffect, useRef, useCallback } from 'react'
import { MOCK_FLOOD_ZONES, CITY_CENTERS } from '../lib/mockData.js'
import { useTheme } from '../lib/ThemeContext.jsx'
import { useFloodPolygons } from '../hooks/useFloodPolygons.js'

// ── Tiles — OpenStreetMap (gratis, tidak butuh API key) ──────────────────────
const TILES = {
  // Dark mode: OSM dengan filter CSS
  dark: {
    url:         'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
  // Light mode: OSM standard
  light: {
    url:         'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
}

// ── Mock zone styles (fallback) ───────────────────────────────────────────────
const MOCK_STYLE = {
  high:   { color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.30, weight: 2 },
  medium: { color: '#f97316', fillColor: '#f97316', fillOpacity: 0.22, weight: 1.5 },
  low:    { color: '#eab308', fillColor: '#eab308', fillOpacity: 0.15, weight: 1 },
}
const MOCK_HOVER = {
  high:   { fillOpacity: 0.55 },
  medium: { fillOpacity: 0.45 },
  low:    { fillOpacity: 0.35 },
}

// Risk level labels sesuai BNPB No.3/2025
const RISK_LABELS = {
  very_high: '🔴 Sangat Tinggi',
  high:      '🟠 Tinggi',
  medium:    '🟡 Sedang',
  low:       '🟢 Rendah',
  very_low:  '🟢 Sangat Rendah',
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

// ── GeoJSON Tooltip (untuk polygon dari InaRisk) ──────────────────────────────
function makeTooltipContent(feature, isDark) {
  const p = feature.properties
  const bg   = isDark ? '#1f2937' : '#ffffff'
  const fg   = isDark ? '#f3f4f6' : '#111827'
  const bdr  = isDark ? '#374151' : '#e5e7eb'

  const content = document.createElement('div')
  content.style.cssText = `background:${bg};color:${fg};border:1px solid ${bdr};border-radius:8px;padding:8px 10px;min-width:160px;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.3)`
  content.innerHTML = `
    <p style="font-weight:700;margin:0 0 4px">${p.name}</p>
    <p style="color:#f97316;margin:0 0 4px">${RISK_LABELS[p.risk] ?? p.risk}</p>
    <p style="opacity:.75;font-size:12px;margin:0">Indeks Bahaya: ${p.hazard?.toFixed(3) ?? 'N/A'}</p>
    ${p.kab ? `<p style="opacity:.55;font-size:11px;font-style:italic;margin:2px 0 0">${p.kab}</p>` : ''}
  `
  return content
}

// ── Live GeoJSON Overlay ──────────────────────────────────────────────────────
function LiveFloodLayer({ geojson, isDark }) {
  const geoJsonRef = useRef(null)

  const styleFeature = useCallback((feature) => {
    const color = feature?.properties?.color ?? '#f97316'
    return {
      color,
      fillColor:   color,
      fillOpacity: 0.30,
      weight:      1.5,
      opacity:     0.9,
    }
  }, [])

  const onEachFeature = useCallback((feature, layer) => {
    const tooltipEl = makeTooltipContent(feature, isDark)
    layer.bindTooltip(tooltipEl, { sticky: true, className: 'inarisk-tooltip' })

    layer.on({
      mouseover: (e) => {
        e.target.setStyle({ fillOpacity: 0.55, weight: 2.5 })
        e.target.bringToFront()
      },
      mouseout: (e) => {
        if (geoJsonRef.current) {
          geoJsonRef.current.resetStyle(e.target)
        }
      },
    })
  }, [isDark])

  if (!geojson) return null

  return (
    <GeoJSON
      ref={geoJsonRef}
      key={`${geojson.city}-${geojson._timestamp}`}
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
            mouseover: e => e.target.setStyle({ ...MOCK_STYLE[zone.risk], ...MOCK_HOVER[zone.risk] }),
            mouseout:  e => e.target.setStyle(MOCK_STYLE[zone.risk]),
          }}
        >
          <Tooltip sticky>
            <div style={{
              background:   isDark ? '#1f2937' : '#ffffff',
              color:        isDark ? '#f3f4f6' : '#111827',
              border:       `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
              borderRadius: '8px', padding: '8px 10px', minWidth: '160px',
              fontSize: '13px', boxShadow: '0 4px 12px rgba(0,0,0,.3)',
            }}>
              <p style={{ fontWeight: 700, marginBottom: 4 }}>{zone.name}</p>
              <p style={{ color: '#f97316', marginBottom: 4 }}>
                {zone.risk === 'high' ? '🔴 Risiko Tinggi' : zone.risk === 'medium' ? '🟠 Risiko Sedang' : '🟡 Risiko Rendah'}
              </p>
              <p style={{ opacity: 0.75, fontSize: 12 }}>
                Est. {zone.pop_est?.toLocaleString('id-ID')} jiwa
              </p>
              <p style={{ opacity: 0.55, fontSize: 11, fontStyle: 'italic', marginTop: 2 }}>
                {zone.note}
              </p>
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
  const bg   = isDark ? 'rgba(17,24,39,0.92)' : 'rgba(255,255,255,0.92)'
  const bdr  = isDark ? '#374151' : '#e2e8f0'
  const txt  = isDark ? '#d1d5db' : '#374151'
  const sub  = isDark ? '#6b7280' : '#94a3b8'

  const levels = isLive ? [
    { color: '#dc2626', label: '🔴 Sangat Tinggi (≥0.8)' },
    { color: '#ef4444', label: '🟠 Tinggi (0.6-0.8)' },
    { color: '#f97316', label: '🟡 Sedang (0.4-0.6)' },
    { color: '#eab308', label: '🟢 Rendah (0.2-0.4)' },
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
        Zona Banjir {isLive ? '(InaRisk BNPB)' : '(Estimasi)'}
      </p>
      {levels.map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: color, opacity: 0.75 }} />
          <span style={{ color: txt }}>{label}</span>
        </div>
      ))}
      <div style={{ borderTop: `1px solid ${bdr}`, paddingTop: 6, marginTop: 4, color: sub }}>
        {isLive ? 'Sumber: InaRisk BNPB 2024' : 'Sumber: Estimasi (bukan data riil)'}
      </div>
    </div>
  )
}


// ── Main Component ────────────────────────────────────────────────────────────
export default function MapView({ selectedCity }) {
  const { theme }  = useTheme()
  const isDark     = theme === 'dark'
  const cityData   = CITY_CENTERS[selectedCity] ?? CITY_CENTERS.semarang

  // Fetch polygon dari InaRisk BNPB
  const { polygons, loading: polygonsLoading } = useFloodPolygons(selectedCity)
  const hasLivePolygons = polygons && polygons.features?.length > 0

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

        {/* Overlay: InaRisk live polygons ATAU mock zones sebagai fallback */}
        {hasLivePolygons
          ? <LiveFloodLayer geojson={polygons} isDark={isDark} />
          : <MockFloodLayer city={selectedCity} isDark={isDark} />
        }
      </MapContainer>

      {/* Legend */}
      <MapLegend isDark={isDark} isLive={hasLivePolygons} />

      {/* Loading indicator saat fetch polygon */}
      {polygonsLoading && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 400, background: isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
          border: `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
          borderRadius: 8, padding: '6px 14px', fontSize: 12,
          color: isDark ? '#93c5fd' : '#3b82f6',
          backdropFilter: 'blur(8px)',
        }}>
          ⟳ Memuat polygon InaRisk BNPB...
        </div>
      )}

      {/* City label */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 400,
        background: isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
        border: `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
        borderRadius: 8, padding: '6px 12px', fontSize: 13, fontWeight: 600,
        color: isDark ? '#f3f4f6' : '#1e293b',
        backdropFilter: 'blur(8px)',
      }}>
        📍 {selectedCity.charAt(0).toUpperCase() + selectedCity.slice(1)}
        {hasLivePolygons && (
          <span style={{ marginLeft: 6, fontSize: 11, color: isDark ? '#6b7280' : '#94a3b8' }}>
            ({polygons.features.length} kec.)
          </span>
        )}
      </div>
    </div>
  )
}
