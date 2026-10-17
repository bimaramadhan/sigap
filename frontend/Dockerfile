# ==========================================
# Stage 1: Build React + Vite SPA
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies dengan package-lock untuk konsistensi build
COPY package*.json ./
RUN npm ci

# Salin source code
COPY . .

# Argument build untuk URL backend API (opsional jika direct API call)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Jalankan build Vite
RUN npm run build

# ==========================================
# Stage 2: Production Server dengan Nginx
# ==========================================
FROM nginx:alpine

# Salin build output ke direktori web root Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Salin template config dan entrypoint
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Port default untuk Google Cloud Run
ENV PORT=8080
ENV BACKEND_URL=http://localhost:8080

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
