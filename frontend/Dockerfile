# ── Stage 1: Build the static frontend assets ───────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files and install
COPY package*.json ./
RUN npm ci

# Copy source code and build Vite production bundle
COPY . .

# Accept VITE_API_BASE_URL build arg from Railway
ARG VITE_API_BASE_URL
RUN npm run build

# ── Stage 2: Serve the build folder with Nginx ──────────────────────────────
FROM nginx:alpine

# Copy build output to Nginx directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Railway-specific Nginx config
COPY railway.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
