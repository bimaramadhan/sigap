/**
 * lib/mockData.js
 * ────────────────
 * Data mock untuk development tanpa backend.
 * Dipakai saat VITE_USE_MOCK=true atau backend tidak bisa dihubungi.
 * Struktur data IDENTIK dengan response FastAPI.
 *
 * v2: Tambah MOCK_WEATHER dengan weather_boost + alert_boost
 *     Update MOCK_VULNERABILITY dengan base_score + dynamic boost fields
 */

export const MOCK_CITIES = [
  { id: 'semarang',  label: 'Kota Semarang',   province: 'Jawa Tengah', bbox: [110.29, -7.11, 110.51, -6.96] },
  { id: 'bekasi',    label: 'Kota/Kab Bekasi',  province: 'Jawa Barat',  bbox: [106.88, -6.38, 107.05, -6.17] },
  { id: 'jakarta',   label: 'DKI Jakarta',      province: 'DKI Jakarta', bbox: [106.68, -6.38, 107.00, -6.08] },
  { id: 'surabaya',  label: 'Kota Surabaya',    province: 'Jawa Timur',  bbox: [112.60, -7.40, 112.85, -7.15] },
]

export const MOCK_ALERTS = {
  fetched_at:   new Date().toISOString(),
  total_alerts: 12,
  flood_alerts: 4,
  alerts: [
    {
      id:              'CST20260922001',
      province:        'Jawa Tengah',
      title:           'Hujan Lebat disertai Petir di Jawa Tengah',
      severity:        'Severe',
      kecamatan_count: 18,
      effective:       new Date().toISOString(),
      expires:         new Date(Date.now() + 3 * 3600000).toISOString(),
      is_flood:        true,
    },
    {
      id:              'CJT20260922002',
      province:        'Jawa Tengah',
      title:           'Hujan Sangat Lebat di Semarang Utara',
      severity:        'Extreme',
      kecamatan_count: 7,
      effective:       new Date().toISOString(),
      expires:         new Date(Date.now() + 2 * 3600000).toISOString(),
      is_flood:        true,
    },
    {
      id:              'CJB20260922003',
      province:        'Jawa Barat',
      title:           'Hujan Lebat di Bekasi dan Sekitarnya',
      severity:        'Moderate',
      kecamatan_count: 11,
      effective:       new Date().toISOString(),
      expires:         new Date(Date.now() + 4 * 3600000).toISOString(),
      is_flood:        true,
    },
    {
      id:              'CDK20260922004',
      province:        'DKI Jakarta',
      title:           'Hujan Lebat disertai Angin Kencang',
      severity:        'Severe',
      kecamatan_count: 23,
      effective:       new Date().toISOString(),
      expires:         new Date(Date.now() + 5 * 3600000).toISOString(),
      is_flood:        true,
    },
  ],
}

// ── Weather Mock ──────────────────────────────────────────────────────────────
// Simulasi kondisi cuaca berbeda per kota untuk demo yang lebih menarik
export const MOCK_WEATHER = {
  semarang: {
    city:                'semarang',
    fetched_at:          new Date().toISOString(),
    rainfall_12h_mm:     68.4,            // hujan lebat → boost +15
    worst_weather_code:  65,
    worst_weather_desc:  'Hujan Lebat',
    worst_weather_emoji: '🌧️',
    weather_risk:        'high',
    boost_score:         15,
    boost_reason:        'Hujan lebat (>50mm/12jam)',
    is_rainy_season:     true,
    kecamatan_count:     5,
    kecamatan_data: [
      { kecamatan: 'Semarang Utara',  area: 'Bandarharjo',    rainfall_12h: 68.4, max_tp_3h: 21.2, worst_weather: 'Hujan Lebat' },
      { kecamatan: 'Genuk',           area: 'Genuksari',       rainfall_12h: 55.1, max_tp_3h: 18.7, worst_weather: 'Hujan Lebat' },
      { kecamatan: 'Tugu',            area: 'Mangkang Kulon',  rainfall_12h: 44.2, max_tp_3h: 15.3, worst_weather: 'Hujan Sedang' },
      { kecamatan: 'Semarang Tengah', area: 'Miroto',          rainfall_12h: 38.6, max_tp_3h: 13.1, worst_weather: 'Hujan Sedang' },
      { kecamatan: 'Pedurungan',      area: 'Penggaron Kidul', rainfall_12h: 31.0, max_tp_3h: 10.4, worst_weather: 'Hujan Ringan' },
    ],
    source: 'BMKG Prakiraan Cuaca API',
  },
  bekasi: {
    city:                'bekasi',
    fetched_at:          new Date().toISOString(),
    rainfall_12h_mm:     12.3,            // hujan ringan → boost +3
    worst_weather_code:  61,
    worst_weather_desc:  'Hujan Ringan',
    worst_weather_emoji: '🌦️',
    weather_risk:        'low',
    boost_score:         3,
    boost_reason:        'Hujan ringan (>5mm/12jam)',
    is_rainy_season:     true,
    kecamatan_count:     4,
    kecamatan_data: [
      { kecamatan: 'Bekasi Utara',  area: 'Harapan Jaya', rainfall_12h: 12.3, max_tp_3h: 4.1, worst_weather: 'Hujan Ringan' },
      { kecamatan: 'Bekasi Barat',  area: 'Bintara',       rainfall_12h: 10.8, max_tp_3h: 3.6, worst_weather: 'Hujan Ringan' },
      { kecamatan: 'Bekasi Selatan',area: 'Marga Jaya',    rainfall_12h:  8.2, max_tp_3h: 2.7, worst_weather: 'Hujan Ringan' },
      { kecamatan: 'Bekasi Timur',  area: 'Aren Jaya',     rainfall_12h:  5.4, max_tp_3h: 1.8, worst_weather: 'Cerah Berawan' },
    ],
    source: 'BMKG Prakiraan Cuaca API',
  },
  jakarta: {
    city:                'jakarta',
    fetched_at:          new Date().toISOString(),
    rainfall_12h_mm:     112.7,           // hujan sangat lebat → boost +25
    worst_weather_code:  80,
    worst_weather_desc:  'Hujan Lebat + Petir',
    worst_weather_emoji: '⛈️',
    weather_risk:        'extreme',
    boost_score:         25,
    boost_reason:        'Hujan sangat lebat (>100mm/12jam)',
    is_rainy_season:     true,
    kecamatan_count:     4,
    kecamatan_data: [
      { kecamatan: 'Penjaringan', area: 'Penjaringan',     rainfall_12h: 112.7, max_tp_3h: 38.2, worst_weather: 'Hujan Lebat + Petir' },
      { kecamatan: 'Cengkareng', area: 'Cengkareng Barat', rainfall_12h:  98.4, max_tp_3h: 32.1, worst_weather: 'Hujan Lebat + Petir' },
      { kecamatan: 'Gambir',     area: 'Gambir',            rainfall_12h:  87.3, max_tp_3h: 28.9, worst_weather: 'Hujan Lebat' },
      { kecamatan: 'Matraman',   area: 'Pisangan Baru',     rainfall_12h:  74.1, max_tp_3h: 24.7, worst_weather: 'Hujan Lebat' },
    ],
    source: 'BMKG Prakiraan Cuaca API',
  },
}

// ── Vulnerability Mock (v2 — include weather/alert boost) ─────────────────────
export const MOCK_VULNERABILITY = {
  semarang: {
    city:              'semarang',
    city_label:        'Kota Semarang',
    score:             87.4,       // 72.4 base + 15 weather boost
    base_score:        72.4,
    category:          '🔴 AWAS',
    category_message:  'Ancaman tinggi, membahayakan masyarakat. Segera lakukan evakuasi.',
    is_sample_data:    true,
    score_breakdown: {
      hazard:     21.8,
      exposure:   18.2,
      vulnerable: 17.5,
      history:     8.9,
      elevation:   6.0,
      weather:    15.0,   // BARU — dari curah hujan
      alert:       0.0,   // BARU — dari severity alert BMKG
    },
    weather_boost:   15.0,
    weather_desc:    'Hujan Lebat',
    weather_risk:    'high',
    alert_boost:      0.0,
    alert_reason:    '',
    flood_ratio_10yr:  0.348,
    total_population:  1653524,
    est_vulnerable:    291021,
    density_per_km2:   4424,
    historical_events: 14,
    elevation_mean:    18.4,
    elevation_min:     -2.0,
    priority_actions: [
      '🌧️  Hujan Lebat terdeteksi — skor naik +15 poin dari baseline',
      '🚨 SEGERA: Aktifkan Posko Darurat Bencana tingkat kota',
      '🚨 SEGERA: Identifikasi dan notifikasi 291,021 warga rentan',
      '🚨 SEGERA: Deploy tim SAR ke titik akses yang berisiko terputus',
      '🌊 34.8% area kota berpotensi terkena banjir',
      '🌊 Sebagian wilayah di bawah permukaan laut (min -2.0m) — risiko rob',
      '📊 14 kejadian banjir historis (2000-2018)',
    ],
    resource_needs: {
      estimated_affected: 229610,
      perahu_minimal:     459,
      titik_evakuasi:     1148,
      tim_sar_minimal:    689,
      logistik_hari:      3,
    },
  },
  bekasi: {
    city:              'bekasi',
    city_label:        'Kota/Kab Bekasi',
    score:             71.1,       // 68.1 base + 3 weather boost
    base_score:        68.1,
    category:          '🟠 SIAGA',
    category_message:  'Ancaman signifikan, masih dapat dikendalikan. Aktifkan kesiapsiagaan.',
    is_sample_data:    true,
    score_breakdown: {
      hazard:     19.2,
      exposure:   22.1,
      vulnerable: 14.3,
      history:     7.5,
      elevation:   5.0,
      weather:     3.0,
      alert:       0.0,
    },
    weather_boost:    3.0,
    weather_desc:    'Hujan Ringan',
    weather_risk:    'low',
    alert_boost:      0.0,
    alert_reason:    '',
    flood_ratio_10yr:  0.319,
    total_population:  2543676,
    est_vulnerable:    388682,
    density_per_km2:   12083,
    historical_events: 18,
    elevation_mean:    19.2,
    elevation_min:     4.0,
    priority_actions: [
      '🌦️  Hujan Ringan terdeteksi — skor naik +3 poin dari baseline',
      '⚠️  Aktifkan kesiapsiagaan: notifikasi koordinator BPBD',
      '⚠️  Siapkan tempat evakuasi untuk 323,547 warga terdampak',
      '📊 18 kejadian banjir historis (2000-2018)',
    ],
    resource_needs: {
      estimated_affected: 323547,
      perahu_minimal:     647,
      titik_evakuasi:     1618,
      tim_sar_minimal:    971,
      logistik_hari:      3,
    },
  },
  jakarta: {
    city:              'jakarta',
    city_label:        'DKI Jakarta',
    score:             100.0,      // 81.3 base + 25 weather (cap 100)
    base_score:         81.3,
    category:          '🔴 AWAS',
    category_message:  'Ancaman tinggi, membahayakan masyarakat. Segera lakukan evakuasi.',
    is_sample_data:    true,
    score_breakdown: {
      hazard:     24.0,
      exposure:   23.5,
      vulnerable: 20.3,
      history:     9.0,
      elevation:   4.5,
      weather:    18.7,   // capped dari 25 supaya total tidak melebihi 100
      alert:       0.0,
    },
    weather_boost:   25.0,
    weather_desc:    'Hujan Lebat + Petir',
    weather_risk:    'extreme',
    alert_boost:      0.0,
    alert_reason:    '',
    flood_ratio_10yr:  0.48,
    total_population:  10560000,
    est_vulnerable:    1858560,
    density_per_km2:   15900,
    historical_events: 22,
    elevation_mean:    8.0,
    elevation_min:     -3.5,
    priority_actions: [
      '⛈️  Hujan Lebat + Petir terdeteksi — skor AWAS',
      '🚨 SEGERA: Aktifkan Posko Darurat tingkat kota',
      '🚨 SEGERA: Identifikasi 1,858,560 warga rentan di zona banjir',
      '🚨 SEGERA: Deploy tim SAR ke Penjaringan, Pluit, Cengkareng',
      '🌊 48% area Jakarta berpotensi terendam',
      '🌊 Pesisir di bawah laut (min -3.5m) — risiko rob ekstrem',
    ],
    resource_needs: {
      estimated_affected: 2027520,
      perahu_minimal:     4055,
      titik_evakuasi:     10138,
      tim_sar_minimal:    6083,
      logistik_hari:      3,
    },
  },
}

export const MOCK_NARASI = {
  semarang: `⛈️ SITUASI AWAS — Kota Semarang saat ini menghadapi ancaman banjir serius. Hujan lebat (68.4mm/12jam) yang sedang terjadi mendorong skor risiko ke level AWAS (87.4/100). Dari 1,653,524 jiwa penduduk, diperkirakan 229,610 jiwa berada di zona terdampak dengan 291,021 warga rentan membutuhkan prioritas evakuasi.

TINDAKAN PRIORITAS:
  1. 🚨 SEGERA: Aktifkan Posko Darurat Bencana tingkat kota
  2. 🚨 SEGERA: Notifikasi 291,021 warga rentan di zona merah (lansia + balita)
  3. 🚨 SEGERA: Deploy tim SAR dan preposisi perahu di Semarang Utara, Genuk, Tugu
  4. 🌧️ Monitor curah hujan — jika mencapai 100mm/12jam, naikkan ke protokol KRITIS penuh
  5. 📞 Aktifkan koordinasi dengan TNI/Polri untuk bantuan evakuasi

Kebutuhan minimal: 459 perahu evakuasi, 689 tim SAR, 1,148 titik pengungsian untuk 229,610 jiwa terdampak.

📊 Semarang memiliki 14 kejadian banjir historis (2000-2018). Semarang Utara, Genuk, dan Tugu adalah titik kritis yang harus diprioritaskan.`,

  bekasi: `⚠️ SITUASI WASPADA — Kota/Kab Bekasi menunjukkan risiko banjir tinggi (71.1/100) dengan hujan ringan (12.3mm/12jam). Kondisi belum kritis namun perlu kesiapsiagaan aktif. Dari 2,543,676 jiwa penduduk, 323,547 jiwa berada di zona potensi terdampak.

TINDAKAN PRIORITAS:
  1. ⚠️ Aktifkan kesiapsiagaan: notifikasi BPBD semua kecamatan
  2. ⚠️ Monitor level Kali Bekasi dan Kali Cikeas setiap jam
  3. ⚠️ Siapkan 1,618 titik pengungsian untuk estimasi terdampak
  4. 📋 Pastikan jalur evakuasi tidak terhalang

Estimasi kebutuhan: 647 perahu, 971 tim SAR.`,

  jakarta: `🚨 SITUASI DARURAT — DKI Jakarta dalam kondisi KRITIS PENUH (skor 100/100). Hujan lebat + petir (112.7mm/12jam) mendorong risiko ke level tertinggi. Lebih dari 2 juta jiwa diperkirakan terdampak.

TINDAKAN PRIORITAS:
  1. 🚨 SEGERA: Aktifkan Emergency Operation Center (EOC) Jakarta
  2. 🚨 SEGERA: Evakuasi wajib seluruh warga di Penjaringan, Pluit, Cengkareng
  3. 🚨 SEGERA: Koordinasi TNI, Polri, PMI untuk operasi evakuasi massal
  4. ⛈️ Badai petir aktif — larang aktivitas di luar ruangan
  5. 🌊 Pantai dan pesisir TUTUP — risiko rob ekstrem

Kebutuhan: 4,055 perahu, 6,083 tim SAR, 10,138 titik pengungsian.`,
}

// Center koordinat untuk peta
export const CITY_CENTERS = {
  semarang: { center: [-7.005, 110.42],  zoom: 12 },
  bekasi:   { center: [-6.24,  106.995], zoom: 12 },
  jakarta:  { center: [-6.21,  106.845], zoom: 11 },
}

// Flood zone polygons untuk peta overlay
export const MOCK_FLOOD_ZONES = {
  semarang: [
    { id: 'smg-utara',  name: 'Semarang Utara',  risk: 'high',   coords: [[-6.97,110.41],[-6.97,110.46],[-7.00,110.46],[-7.00,110.41]], pop_est: 48000, note: 'Area rob — elevasi di bawah permukaan laut' },
    { id: 'smg-genuk',  name: 'Genuk',            risk: 'medium', coords: [[-6.99,110.45],[-6.99,110.50],[-7.03,110.50],[-7.03,110.45]], pop_est: 95000, note: 'Dataran rendah dekat pantai' },
    { id: 'smg-tugu',   name: 'Tugu',             risk: 'high',   coords: [[-6.97,110.29],[-6.97,110.36],[-7.02,110.36],[-7.02,110.29]], pop_est: 72000, note: 'Area industri — drainase terbatas' },
    { id: 'smg-tengah', name: 'Semarang Tengah',  risk: 'low',    coords: [[-6.99,110.39],[-6.99,110.42],[-7.02,110.42],[-7.02,110.39]], pop_est: 71000, note: 'Area komersial — risiko sedang' },
  ],
  bekasi: [
    { id: 'bks-barat',  name: 'Bekasi Barat',  risk: 'high',   coords: [[-6.22,106.98],[-6.22,107.00],[-6.26,107.00],[-6.26,106.98]], pop_est: 240000, note: 'Bantaran Kali Bekasi' },
    { id: 'bks-utara',  name: 'Bekasi Utara',  risk: 'medium', coords: [[-6.17,106.99],[-6.17,107.03],[-6.22,107.03],[-6.22,106.99]], pop_est: 180000, note: 'Daerah rendah' },
  ],
  jakarta: [
    { id: 'jkt-utara',  name: 'Jakarta Utara', risk: 'high',   coords: [[-6.08,106.74],[-6.08,106.96],[-6.15,106.96],[-6.15,106.74]], pop_est: 1700000, note: 'Pesisir — rob + banjir' },
    { id: 'jkt-barat',  name: 'Jakarta Barat', risk: 'high',   coords: [[-6.15,106.68],[-6.15,106.82],[-6.28,106.82],[-6.28,106.68]], pop_est: 2400000, note: 'Bantaran sungai' },
    { id: 'jkt-pusat',  name: 'Jakarta Pusat', risk: 'medium', coords: [[-6.15,106.82],[-6.15,106.90],[-6.23,106.90],[-6.23,106.82]], pop_est:  900000, note: 'Risiko sedang' },
  ],
}


// ── Flood Report Mock Data ────────────────────────────────────────────────────
// Cuplikan kecil dari wilayah.sql. Mode live memakai seluruh desa kota itu.

export const MOCK_VILLAGES = {
  semarang: [
    {
      kecamatan: 'Semarang Tengah', kecamatan_kode: '33.74.01', kota_administrasi: 'Kota Semarang',
      villages: [{ kode: '33.74.01.1001', nama: 'Miroto' }],
    },
    {
      kecamatan: 'Semarang Utara', kecamatan_kode: '33.74.02', kota_administrasi: 'Kota Semarang',
      villages: [
        { kode: '33.74.02.1001', nama: 'Bandarharjo' },
        { kode: '33.74.02.1008', nama: 'Tanjung Mas' },
      ],
    },
  ],
  bekasi: [
    {
      kecamatan: 'Bekasi Barat', kecamatan_kode: '32.75.02', kota_administrasi: 'Kota Bekasi',
      villages: [{ kode: '32.75.02.1001', nama: 'Bintara' }],
    },
    {
      kecamatan: 'Bekasi Utara', kecamatan_kode: '32.75.03', kota_administrasi: 'Kota Bekasi',
      villages: [{ kode: '32.75.03.1006', nama: 'Harapanjaya' }],
    },
  ],
  jakarta: [
    {
      kecamatan: 'Gambir', kecamatan_kode: '31.71.01', kota_administrasi: 'Kota Administrasi Jakarta Pusat',
      villages: [{ kode: '31.71.01.1001', nama: 'Gambir' }],
    },
    {
      kecamatan: 'Penjaringan', kecamatan_kode: '31.72.01', kota_administrasi: 'Kota Administrasi Jakarta Utara',
      villages: [{ kode: '31.72.01.1001', nama: 'Penjaringan' }],
    },
  ],
}

// Laporan lapangan default kosong — user yang mengisi saat demo
export const MOCK_FLOOD_REPORTS = {
  semarang: { city: 'semarang', report_count: 0, latest_boost: 0, boost_reason: '', reports: [] },
  bekasi:   { city: 'bekasi',   report_count: 0, latest_boost: 0, boost_reason: '', reports: [] },
  jakarta:  { city: 'jakarta',  report_count: 0, latest_boost: 0, boost_reason: '', reports: [] },
}

// In-memory mock store untuk simulasi submit tanpa backend
let _mockReportStore = {
  semarang: [],
  bekasi:   [],
  jakarta:  [],
}

export function getMockReports(city) {
  return _mockReportStore[city] ?? []
}

function findMockVillage(city, kode) {
  for (const group of MOCK_VILLAGES[city] ?? []) {
    const village = group.villages.find(v => v.kode === kode)
    if (village) {
      return {
        ...village,
        kecamatan: group.kecamatan,
        kecamatan_kode: group.kecamatan_kode,
      }
    }
  }
  return null
}

export function addMockReport(data) {
  const city   = data.city?.toLowerCase() ?? 'semarang'
  const levels = { normal: 0, waspada: 8, siaga: 15, awas: 25 }
  const level  = data.flood_level ?? 'normal'
  const boost  = levels[level] ?? 0
  const village = findMockVillage(city, data.desa_kode) ?? {
    kode: data.desa_kode,
    nama: data.desa_kode,
    kecamatan: '',
    kecamatan_kode: '',
  }

  const LABELS = { normal: '🟢 Normal', waspada: '🟡 Waspada', siaga: '🟠 Siaga', awas: '🔴 Awas' }
  const reason = `Desa ${village.nama}, Kec. ${village.kecamatan} — ${level.toUpperCase()} (+${boost})`

  const report = {
    id:                `${city}_${Date.now()}`,
    city,
    reported_at:       new Date().toISOString(),
    reporter:          data.reporter || 'Koordinator BPBD',
    desa_kode:         village.kode,
    desa_name:         village.nama,
    kecamatan:         village.kecamatan,
    kecamatan_kode:    village.kecamatan_kode,
    flood_level:       level,
    flood_level_label: LABELS[level] ?? '🟢 Normal',
    notes:             data.notes ?? '',
    boost_score:       boost,
    boost_breakdown: {
      total:       boost,
      level_boost: boost,
      flood_level: level,
      reason,
    },
  }

  if (!_mockReportStore[city]) _mockReportStore[city] = []
  _mockReportStore[city].unshift(report)
  _mockReportStore[city] = _mockReportStore[city].slice(0, 20)
  return report
}

export function clearMockReports(city) {
  _mockReportStore[city] = []
}

// ── Surabaya additions ────────────────────────────────────────────────────────

// Tambahkan alert Surabaya ke MOCK_ALERTS (extend setelah file dimuat)
MOCK_ALERTS.alerts.push({
  id:              'CJT20260922005',
  province:        'Jawa Timur',
  title:           'Hujan Lebat disertai Petir di Jawa Timur',
  severity:        'Severe',
  kecamatan_count: 14,
  effective:       new Date().toISOString(),
  expires:         new Date(Date.now() + 4 * 3600000).toISOString(),
  is_flood:        true,
})

// Vulnerability mock Surabaya
MOCK_VULNERABILITY.surabaya = {
  city:              'surabaya',
  city_label:        'Kota Surabaya',
  score:             76.2,
  base_score:        63.5,
  category:          '🔴 AWAS',
  category_message:  'Ancaman tinggi, membahayakan masyarakat. Segera lakukan evakuasi.',
  is_sample_data:    true,
  score_breakdown: {
    hazard:     22.4,
    exposure:   20.1,
    vulnerable: 12.8,
    history:     6.7,
    elevation:   8.0,
    weather:    12.7,
    alert:       0.0,
  },
  weather_boost:   12.7,
  weather_desc:    'Hujan Sedang',
  weather_risk:    'medium',
  alert_boost:      0.0,
  alert_reason:    '',
  flood_ratio_10yr:  0.52,
  total_population:  2874699,
  est_vulnerable:    506147,
  density_per_km2:   8463,
  historical_events: 12,
  elevation_mean:    4.5,
  elevation_min:     0.0,
  priority_actions: [
    '🌧️  Hujan Sedang terdeteksi — skor naik +12.7 poin dari baseline',
    '🚨 SEGERA: Aktifkan Posko Darurat Bencana tingkat kota',
    '🚨 SEGERA: Identifikasi 506,147 warga rentan di zona banjir',
    '🌊 52% area Surabaya berpotensi terkena banjir',
    '🌊 Area pesisir Kenjeran, Bulak, Semampir prioritas utama',
    '📊 12 kejadian banjir historis (2000-2018)',
  ],
  resource_needs: {
    estimated_affected: 596576,
    perahu_minimal:     1193,
    titik_evakuasi:     2983,
    tim_sar_minimal:    1790,
    logistik_hari:      3,
  },
}

// Weather mock Surabaya
MOCK_WEATHER.surabaya = {
  city:                'surabaya',
  fetched_at:          new Date().toISOString(),
  rainfall_12h_mm:     23.8,
  worst_weather_code:  63,
  worst_weather_desc:  'Hujan Sedang',
  worst_weather_emoji: '🌧️',
  weather_risk:        'medium',
  boost_score:         8,
  boost_reason:        'Hujan sedang (>20mm/12jam)',
  is_rainy_season:     true,
  kecamatan_count:     5,
  kecamatan_data: [
    { kecamatan: 'Kenjeran',        area: 'Bulak Banteng',  rainfall_12h: 23.8, max_tp_3h: 8.1, worst_weather: 'Hujan Sedang' },
    { kecamatan: 'Semampir',        area: 'Ujung',           rainfall_12h: 21.4, max_tp_3h: 7.3, worst_weather: 'Hujan Sedang' },
    { kecamatan: 'Pabean Cantikan', area: 'Nyamplungan',     rainfall_12h: 19.2, max_tp_3h: 6.5, worst_weather: 'Hujan Ringan' },
    { kecamatan: 'Bulak',           area: 'Kedung Cowek',    rainfall_12h: 17.1, max_tp_3h: 5.8, worst_weather: 'Hujan Ringan' },
    { kecamatan: 'Bubutan',         area: 'Gundih',          rainfall_12h: 12.3, max_tp_3h: 4.2, worst_weather: 'Hujan Ringan' },
  ],
  source: 'BMKG Prakiraan Cuaca API',
}

// Narasi mock Surabaya
MOCK_NARASI.surabaya = `🚨 SITUASI AWAS — Kota Surabaya dalam kondisi risiko banjir tinggi (76.2/100). Hujan sedang (23.8mm/12jam) memperburuk kondisi di area pesisir utara. Dari 2,874,699 jiwa penduduk, diperkirakan 596,576 jiwa di zona terdampak dengan 506,147 warga rentan membutuhkan perhatian khusus.

TINDAKAN PRIORITAS:
  1. 🚨 SEGERA: Aktifkan Posko Darurat Bencana tingkat kota
  2. 🚨 SEGERA: Prioritaskan evakuasi Kenjeran, Bulak, Semampir — area pesisir paling rawan
  3. 🌊 Monitor level Kali Mas dan Kali Surabaya setiap 1 jam
  4. 🚨 Siapkan 2,983 titik pengungsian untuk 596,576 jiwa terdampak
  5. 📞 Koordinasi TNI/Polri untuk bantuan evakuasi pesisir utara

Kebutuhan minimal: 1,193 perahu, 1,790 tim SAR, 2,983 titik pengungsian.`

// City center dan flood zones Surabaya
CITY_CENTERS.surabaya = { center: [-7.265, 112.74], zoom: 12 }

MOCK_FLOOD_ZONES.surabaya = [
  { id: 'sby-kenjeran',  name: 'Kenjeran',        risk: 'high',   coords: [[-7.19,112.76],[-7.19,112.79],[-7.24,112.79],[-7.24,112.76]], pop_est: 180000, note: 'Area pesisir — rawan banjir rob' },
  { id: 'sby-semampir',  name: 'Semampir',         risk: 'high',   coords: [[-7.20,112.72],[-7.20,112.76],[-7.24,112.76],[-7.24,112.72]], pop_est: 220000, note: 'Dekat pelabuhan — sering banjir' },
  { id: 'sby-pabean',    name: 'Pabean Cantikan',  risk: 'medium', coords: [[-7.21,112.72],[-7.21,112.74],[-7.23,112.74],[-7.23,112.72]], pop_est: 95000,  note: 'Area kota tua — drainase lama' },
  { id: 'sby-bubutan',   name: 'Bubutan',          risk: 'low',    coords: [[-7.24,112.72],[-7.24,112.74],[-7.27,112.74],[-7.27,112.72]], pop_est: 120000, note: 'Bantaran Kali Mas' },
]

MOCK_VILLAGES.surabaya = [
  {
    kecamatan: 'Semampir', kecamatan_kode: '35.78.16', kota_administrasi: 'Kota Surabaya',
    villages: [{ kode: '35.78.16.1004', nama: 'Ujung' }],
  },
  {
    kecamatan: 'Kenjeran', kecamatan_kode: '35.78.17', kota_administrasi: 'Kota Surabaya',
    villages: [{ kode: '35.78.17.1003', nama: 'Bulak Banteng' }],
  },
]

MOCK_FLOOD_REPORTS.surabaya = { city: 'surabaya', report_count: 0, latest_boost: 0, boost_reason: '', reports: [] }
_mockReportStore.surabaya = []
