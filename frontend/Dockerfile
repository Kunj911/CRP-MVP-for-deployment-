# ── Stage 1: Build the static frontend assets ───────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files and install
# NOTE: Build context is the REPO ROOT (not frontend/)
COPY frontend/package*.json ./
RUN npm ci

# Copy source code and build Vite production bundle
COPY frontend/ .
RUN npm run build

# ── Stage 2: Serve the build folder with Nginx ──────────────────────────────
FROM nginx:alpine

# Copy build output to Nginx directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Railway-specific Nginx config template
# The official nginx image auto-runs envsubst on files in /etc/nginx/templates/
# replacing ${PORT} with the value of the PORT environment variable
COPY nginx/railway.conf /etc/nginx/templates/default.conf.template

# Railway assigns PORT dynamically — default to 80
ENV PORT=80
EXPOSE ${PORT}

CMD ["nginx", "-g", "daemon off;"]
