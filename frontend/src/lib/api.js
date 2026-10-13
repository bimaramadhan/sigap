/**
 * lib/api.js — v3
 * ─────────────────
 * Semua HTTP calls ke FastAPI backend.
 * Otomatis fallback ke mock data jika backend tidak tersedia.
 *
 * v3: Tambah flood report functions (submit, get, villages, clear)
 */

import axios from 'axios'
import {
  MOCK_ALERTS,
  MOCK_VULNERABILITY,
  MOCK_WEATHER,
  MOCK_NARASI,
  MOCK_CITIES,
  MOCK_VILLAGES,
  getMockReports,
  addMockReport,
  clearMockReports,
} from './mockData.js'

const BASE_URL = '/api'
const http     = axios.create({ baseURL: BASE_URL, timeout: 120000 })
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const delay    = (ms = 600) => new Promise(r => setTimeout(r, ms))

const MOCK_ALIAS = {
  '33.74': 'semarang',
  '32.75': 'bekasi',
  '35.78': 'surabaya',
  '31.71': 'jakarta',
  '31.72': 'jakarta',
  '31.73': 'jakarta',
  '31.74': 'jakarta',
  '31.75': 'jakarta',
}

function mockCity(table, city, fallback = 'semarang') {
  if (!table) return undefined
  return table[city] ?? table[MOCK_ALIAS[city]] ?? table[fallback]
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function getCities() {
  if (USE_MOCK) { await delay(200); return { cities: MOCK_CITIES } }
  try { return (await http.get('/cities')).data }
  catch { return { cities: MOCK_CITIES } }
}

export async function getCity(kode) {
  if (USE_MOCK) {
    await delay(200)
    return MOCK_CITIES.find(city => city.id === kode) ?? MOCK_CITIES[0]
  }
  try { return (await http.get(`/cities/${kode}`)).data }
  catch { return MOCK_CITIES.find(city => city.id === kode) ?? { id: kode, label: kode, bbox: null } }
}

export async function getAlerts(floodOnly = true, city = null) {
  if (USE_MOCK) { await delay(800); return MOCK_ALERTS }
  try {
    const params = { flood_only: floodOnly }
    if (city) params.city = city
    return (await http.get('/alerts', { params })).data
  }
  catch { console.warn('Fallback → mock alerts'); return MOCK_ALERTS }
}

export async function getWeather(city) {
  if (USE_MOCK) {
    await delay(700)
    return mockCity(MOCK_WEATHER, city)
  }
  try { return (await http.get(`/weather/${city}`)).data }
  catch {
    console.warn(`Fallback → mock weather (${city})`)
    return mockCity(MOCK_WEATHER, city)
  }
}

export async function getVulnerability(city) {
  if (USE_MOCK) {
    await delay(1000)
    return mockCity(MOCK_VULNERABILITY, city)
  }
  try { return (await http.get(`/vulnerability/${city}`)).data }
  catch {
    console.warn(`Fallback → mock vulnerability (${city})`)
    return mockCity(MOCK_VULNERABILITY, city)
  }
}

export async function getNarasi(city, useGemini = true) {
  if (USE_MOCK) {
    await delay(1200)
    return {
      city,
      score:       mockCity(MOCK_VULNERABILITY, city)?.score ?? 70,
      category:    mockCity(MOCK_VULNERABILITY, city)?.category ?? '🟠 TINGGI',
      narasi:      mockCity(MOCK_NARASI, city),
      source:      'template',
      model:       'mock',
      generated_at:new Date().toISOString(),
    }
  }
  try {
    return (await http.get(`/narasi/${city}`, { params: { use_gemini: useGemini } })).data
  } catch {
    console.warn(`Fallback → mock narasi (${city})`)
    return {
      city,
      score:       mockCity(MOCK_VULNERABILITY, city)?.score ?? 70,
      category:    mockCity(MOCK_VULNERABILITY, city)?.category ?? '🟠 TINGGI',
      narasi:      mockCity(MOCK_NARASI, city),
      source:      'template',
      model:       'mock',
      generated_at:new Date().toISOString(),
    }
  }
}

export async function getFullAnalysis(city) {
  if (USE_MOCK) {
    await delay(1500)
    const vuln   = mockCity(MOCK_VULNERABILITY, city)
    const narasi = mockCity(MOCK_NARASI, city)
    const weather= mockCity(MOCK_WEATHER, city)
    return {
      city,
      analyzed_at:   new Date().toISOString(),
      active_alerts: MOCK_ALERTS.alerts.slice(0, 3),
      weather,
      vulnerability: vuln,
      narasi: {
        city, score: vuln.score, category: vuln.category,
        narasi, source: 'template', model: 'mock',
        generated_at: new Date().toISOString(),
      },
      is_sample_data: true,
    }
  }
  try { return (await http.get(`/analyze/${city}`)).data }
  catch {
    const vuln   = mockCity(MOCK_VULNERABILITY, city)
    const weather= mockCity(MOCK_WEATHER, city)
    return {
      city, analyzed_at: new Date().toISOString(),
      active_alerts: MOCK_ALERTS.alerts.slice(0, 3),
      weather,
      vulnerability: vuln,
      narasi: {
        city, score: vuln.score, category: vuln.category,
        narasi: mockCity(MOCK_NARASI, city),
        source: 'template', model: 'mock',
        generated_at: new Date().toISOString(),
      },
      is_sample_data: true,
    }
  }
}

// ── Flood Report API ──────────────────────────────────────────────────────────

function kecamatanBoostsFrom(reports) {
  const out = {}
  for (const report of reports) {
    if (!report.kecamatan) continue
    const prev = out[report.kecamatan]
    if (prev && report.boost_score <= prev.boost_score) continue
    out[report.kecamatan] = {
      boost_score: report.boost_score,
      flood_level: report.flood_level,
      desa_name:   report.desa_name,
      reason:      report.boost_breakdown?.reason ?? '',
    }
  }
  return out
}

export async function getFloodVillages(city) {
  if (USE_MOCK) {
    await delay(200)
    return { city, groups: mockCity(MOCK_VILLAGES, city) ?? [] }
  }
  try { return (await http.get(`/flood-villages/${city}`)).data }
  catch { return { city, groups: mockCity(MOCK_VILLAGES, city) ?? [] } }
}

export async function getFloodReports(city) {
  if (USE_MOCK) {
    await delay(300)
    const reports = getMockReports(city)
    const best    = reports.length > 0
      ? Math.max(...reports.map(r => r.boost_score))
      : 0
    const reason  = reports[0]?.boost_breakdown?.reason ?? ''
    return {
      city,
      report_count: reports.length,
      latest_boost: best,
      boost_reason: reason,
      reports,
      kecamatan_boosts: kecamatanBoostsFrom(reports),
    }
  }
  try { return (await http.get(`/flood-reports/${city}`)).data }
  catch {
    const reports = getMockReports(city)
    return {
      city,
      report_count: reports.length,
      latest_boost: 0,
      boost_reason: '',
      reports,
      kecamatan_boosts: {},
    }
  }
}

export async function submitFloodReport(data) {
  if (USE_MOCK) {
    await delay(600)
    return addMockReport(data)
  }
  try { return (await http.post('/flood-report', data)).data }
  catch (e) {
    // Fallback ke mock jika backend tidak tersedia
    console.warn('Backend tidak tersedia — simpan ke mock store')
    return addMockReport(data)
  }
}

export async function clearFloodReports(city) {
  if (USE_MOCK) {
    await delay(300)
    clearMockReports(city)
    return { city, cleared: 0 }
  }
  try { return (await http.delete(`/flood-reports/${city}`)).data }
  catch {
    clearMockReports(city)
    return { city, cleared: 0 }
  }
}

// ── Flood Polygon API ─────────────────────────────────────────────────────────

export async function getFloodPolygons(city) {
  if (USE_MOCK) {
    // Dalam mock mode, return null — MapView akan pakai MOCK_FLOOD_ZONES
    return null
  }
  try {
    const { data } = await http.get(`/flood-polygons/${city}`, { timeout: 120000 })
    return data
  } catch (e) {
    console.warn(`Flood polygon tidak tersedia (${city}), pakai mock zones`)
    return null
  }
}

export async function getVulnerabilityMap(city) {
  if (USE_MOCK) return null   // mock mode: MapView pakai flood polygons biasa
  try {
    const { data } = await http.get(`/vulnerability-map/${city}`, { timeout: 120000 })
    return data
  } catch (e) {
    console.warn(`Vulnerability map tidak tersedia (${city}), fallback ke flood polygons`)
    return null
  }
}
