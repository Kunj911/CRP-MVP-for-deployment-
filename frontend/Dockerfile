# Stage 1: Build the static frontend assets
FROM node:20-alpine as builder

WORKDIR /app

# Copy dependency files and install
COPY frontend/package*.json ./
RUN npm ci

# Copy code and build Vite production bundle
COPY frontend/ .
RUN npm run build

# Stage 2: Serve the build folder with Nginx
FROM nginx:alpine

# Copy build output to Nginx directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx SPA configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
