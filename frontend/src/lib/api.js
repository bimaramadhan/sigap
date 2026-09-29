/**
 * lib/api.js — v3
 * ─────────────────
 * Semua HTTP calls ke FastAPI backend.
 * Otomatis fallback ke mock data jika backend tidak tersedia.
 *
 * v3: Tambah flood report functions (submit, get, rivers, clear)
 */

import axios from 'axios'
import {
  MOCK_ALERTS,
  MOCK_VULNERABILITY,
  MOCK_WEATHER,
  MOCK_NARASI,
  MOCK_CITIES,
  MOCK_RIVERS,
  MOCK_FLOOD_REPORTS,
  getMockReports,
  addMockReport,
  clearMockReports,
} from './mockData.js'

const BASE_URL = '/api'
const http     = axios.create({ baseURL: BASE_URL, timeout: 15000 })
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const delay    = (ms = 600) => new Promise(r => setTimeout(r, ms))

// ── API Functions ─────────────────────────────────────────────────────────────

export async function getCities() {
  if (USE_MOCK) { await delay(200); return { cities: MOCK_CITIES } }
  try { return (await http.get('/cities')).data }
  catch { return { cities: MOCK_CITIES } }
}

export async function getAlerts(floodOnly = true) {
  if (USE_MOCK) { await delay(800); return MOCK_ALERTS }
  try { return (await http.get('/alerts', { params: { flood_only: floodOnly } })).data }
  catch { console.warn('Fallback → mock alerts'); return MOCK_ALERTS }
}

export async function getWeather(city) {
  if (USE_MOCK) {
    await delay(700)
    return MOCK_WEATHER[city] ?? MOCK_WEATHER.semarang
  }
  try { return (await http.get(`/weather/${city}`)).data }
  catch {
    console.warn(`Fallback → mock weather (${city})`)
    return MOCK_WEATHER[city] ?? MOCK_WEATHER.semarang
  }
}

export async function getVulnerability(city) {
  if (USE_MOCK) {
    await delay(1000)
    return MOCK_VULNERABILITY[city] ?? MOCK_VULNERABILITY.semarang
  }
  try { return (await http.get(`/vulnerability/${city}`)).data }
  catch {
    console.warn(`Fallback → mock vulnerability (${city})`)
    return MOCK_VULNERABILITY[city] ?? MOCK_VULNERABILITY.semarang
  }
}

export async function getNarasi(city, useGemini = true) {
  if (USE_MOCK) {
    await delay(1200)
    return {
      city,
      score:       MOCK_VULNERABILITY[city]?.score ?? 70,
      category:    MOCK_VULNERABILITY[city]?.category ?? '🟠 TINGGI',
      narasi:      MOCK_NARASI[city] ?? MOCK_NARASI.semarang,
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
      score:       MOCK_VULNERABILITY[city]?.score ?? 70,
      category:    MOCK_VULNERABILITY[city]?.category ?? '🟠 TINGGI',
      narasi:      MOCK_NARASI[city] ?? MOCK_NARASI.semarang,
      source:      'template',
      model:       'mock',
      generated_at:new Date().toISOString(),
    }
  }
}

export async function getFullAnalysis(city) {
  if (USE_MOCK) {
    await delay(1500)
    const vuln   = MOCK_VULNERABILITY[city] ?? MOCK_VULNERABILITY.semarang
    const narasi = MOCK_NARASI[city] ?? MOCK_NARASI.semarang
    const weather= MOCK_WEATHER[city] ?? MOCK_WEATHER.semarang
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
    const vuln   = MOCK_VULNERABILITY[city] ?? MOCK_VULNERABILITY.semarang
    const weather= MOCK_WEATHER[city] ?? MOCK_WEATHER.semarang
    return {
      city, analyzed_at: new Date().toISOString(),
      active_alerts: MOCK_ALERTS.alerts.slice(0, 3),
      weather,
      vulnerability: vuln,
      narasi: {
        city, score: vuln.score, category: vuln.category,
        narasi: MOCK_NARASI[city] ?? MOCK_NARASI.semarang,
        source: 'template', model: 'mock',
        generated_at: new Date().toISOString(),
      },
      is_sample_data: true,
    }
  }
}

// ── Flood Report API (v3) ─────────────────────────────────────────────────────
// getMockReports, addMockReport, clearMockReports, MOCK_RIVERS sudah diimport di atas

export async function getFloodRivers(city) {
  if (USE_MOCK) {
    await delay(200)
    return { city, rivers: MOCK_RIVERS[city] ?? [] }
  }
  try { return (await http.get(`/flood-rivers/${city}`)).data }
  catch { return { city, rivers: MOCK_RIVERS[city] ?? [] } }
}

export async function getFloodReports(city) {
  if (USE_MOCK) {
    await delay(300)
    const reports = getMockReports(city)
    const best    = reports.length > 0
      ? Math.max(...reports.map(r => r.boost_score))
      : 0
    const reason  = reports[0]?.boost_breakdown?.reason ?? ''
    return { city, report_count: reports.length, latest_boost: best, boost_reason: reason, reports }
  }
  try { return (await http.get(`/flood-reports/${city}`)).data }
  catch {
    const reports = getMockReports(city)
    return { city, report_count: reports.length, latest_boost: 0, boost_reason: '', reports }
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
