import { MapContainer, TileLayer, Polygon, Tooltip, ZoomControl, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import { MOCK_FLOOD_ZONES, CITY_CENTERS } from '../lib/mockData.js'
import { useTheme } from '../lib/ThemeContext.jsx'

// OpenStreetMap-based tiles — 100% gratis, tidak butuh API key apapun
const TILES = {
  dark: {
    // Stadia Maps Alidade Smooth Dark — gratis tanpa API key untuk dev/hackathon
    url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  light: {
    // OpenStreetMap standard — paling reliable, selalu gratis
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
  },
}

const RISK_STYLE = {
  high:   { color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.30, weight: 2 },
  medium: { color: '#f97316', fillColor: '#f97316', fillOpacity: 0.22, weight: 1.5 },
  low:    { color: '#eab308', fillColor: '#eab308', fillOpacity: 0.15, weight: 1 },
}

const RISK_HOVER = {
  high:   { fillOpacity: 0.55 },
  medium: { fillOpacity: 0.45 },
  low:    { fillOpacity: 0.35 },
}

const RISK_LABEL = {
  high:   '🔴 Risiko Tinggi',
  medium: '🟠 Risiko Sedang',
  low:    '🟡 Risiko Rendah',
}

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

function ZoneTooltip({ zone, isDark }) {
  return (
    <Tooltip sticky>
      <div style={{
        background:   isDark ? '#1f2937' : '#ffffff',
        color:        isDark ? '#f3f4f6' : '#111827',
        border:       `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
        borderRadius: '8px',
        padding:      '8px 10px',
        minWidth:     '160px',
        fontSize:     '13px',
        boxShadow:    '0 4px 12px rgba(0,0,0,0.3)',
      }}>
        <p style={{ fontWeight: 700, marginBottom: 4 }}>{zone.name}</p>
        <p style={{ color: '#f97316', marginBottom: 4 }}>{RISK_LABEL[zone.risk]}</p>
        <p style={{ opacity: 0.75, fontSize: 12 }}>
          Est. {zone.pop_est.toLocaleString('id-ID')} jiwa
        </p>
        <p style={{ opacity: 0.55, fontSize: 11, fontStyle: 'italic', marginTop: 2 }}>
          {zone.note}
        </p>
      </div>
    </Tooltip>
  )
}

function MapLegend({ isDark }) {
  const bg     = isDark ? 'rgba(17,24,39,0.92)' : 'rgba(255,255,255,0.92)'
  const border = isDark ? '#374151' : '#e2e8f0'
  const text   = isDark ? '#d1d5db' : '#374151'
  const sub    = isDark ? '#6b7280' : '#94a3b8'

  return (
    <div style={{
      position:       'absolute',
      bottom:         20,
      left:           12,
      zIndex:         400,
      background:     bg,
      border:         `1px solid ${border}`,
      borderRadius:   12,
      padding:        '10px 14px',
      fontSize:       12,
      backdropFilter: 'blur(8px)',
      boxShadow:      '0 4px 16px rgba(0,0,0,0.25)',
    }}>
      <p style={{ color: text, fontWeight: 600, marginBottom: 8 }}>Zona Banjir</p>
      {Object.entries(RISK_LABEL).map(([risk, label]) => (
        <div key={risk} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <div style={{
            width: 12, height: 12, borderRadius: 3,
            background: RISK_STYLE[risk].color, opacity: 0.75,
          }} />
          <span style={{ color: text }}>{label}</span>
        </div>
      ))}
      <div style={{ borderTop: `1px solid ${border}`, paddingTop: 6, marginTop: 4, color: sub }}>
        Sumber: JRC GloFAS + BNPB
      </div>
    </div>
  )
}

export default function MapView({ selectedCity }) {
  const { theme }  = useTheme()
  const isDark     = theme === 'dark'
  const cityData   = CITY_CENTERS[selectedCity] ?? CITY_CENTERS.semarang
  const floodZones = MOCK_FLOOD_ZONES[selectedCity] ?? []

  // Leaflet WAJIB punya height dalam pixels — bukan % dari flex parent
  // Solusi: pakai viewport height dikurangi header (~56px) + tab bar (~0) + status bar (~36px)
  const mapHeight = 'calc(100vh - 56px - 36px - 24px)'

  return (
    <div style={{ position: 'relative', width: '100%', height: mapHeight }}>
      <MapContainer
        center={cityData.center}
        zoom={cityData.zoom}
        zoomControl={false}
        style={{
          width:        '100%',
          height:       '100%',
          borderRadius: '0.75rem',
          background:   isDark ? '#111827' : '#e2e8f0',
        }}
      >
        <ThemeTileLayer />
        <FlyToCity city={selectedCity} />
        <ZoomControl position="bottomright" />

        {floodZones.map(zone => (
          <Polygon
            key={zone.id}
            positions={zone.coords}
            pathOptions={RISK_STYLE[zone.risk] ?? RISK_STYLE.low}
            eventHandlers={{
              mouseover: e => e.target.setStyle({ ...RISK_STYLE[zone.risk], ...RISK_HOVER[zone.risk] }),
              mouseout:  e => e.target.setStyle(RISK_STYLE[zone.risk]),
            }}
          >
            <ZoneTooltip zone={zone} isDark={isDark} />
          </Polygon>
        ))}
      </MapContainer>

      <MapLegend isDark={isDark} />

      <div style={{
        position:       'absolute',
        top:            12,
        right:          12,
        zIndex:         400,
        background:     isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
        border:         `1px solid ${isDark ? '#374151' : '#e2e8f0'}`,
        borderRadius:   8,
        padding:        '6px 12px',
        fontSize:       13,
        fontWeight:     600,
        color:          isDark ? '#f3f4f6' : '#1e293b',
        backdropFilter: 'blur(8px)',
      }}>
        📍 {selectedCity.charAt(0).toUpperCase() + selectedCity.slice(1)}
      </div>
    </div>
  )
}
