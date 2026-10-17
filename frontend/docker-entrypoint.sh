#!/bin/sh
set -e

# Default port ke 8080 (standar Cloud Run) jika tidak diset
export PORT="${PORT:-8080}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"
export BACKEND_URL="${BACKEND_URL%/}"

# Substitusi hanya variabel ${PORT} dan ${BACKEND_URL} agar variabel Nginx bawaan ($uri, $host, dll) tidak hilang
envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"
