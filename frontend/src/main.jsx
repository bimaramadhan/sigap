// Leaflet CSS — import SEBELUM index.css supaya z-index override bekerja
import 'leaflet/dist/leaflet.css'

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ThemeProvider } from './lib/ThemeContext.jsx'
import { LanguageProvider } from './lib/LanguageContext.jsx'
import { AuthProvider } from './lib/AuthContext.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  </React.StrictMode>
)
