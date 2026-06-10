import { defineRailway, project, service } from "railway/iac";

export default defineRailway(() => {
  const db = service("MySQL", {
    template: "mysql",
    volumes: [{ name: "mysql-volume", mountPath: "/var/lib/mysql" }],
  });

  const redis = service("Redis", {
    template: "redis",
    volumes: [{ name: "redis-volume", mountPath: "/data" }],
  });

  const backend = service("backend", {
    rootDirectory: "backend",
    build: "docker build -f Dockerfile -t backend .",
    start: "uvicorn main:app --host 0.0.0.0 --port $PORT",
    healthcheckPath: "/health",
    env: {
      APP_ENV: "production",
      DEBUG: "false",
      DB_HOST: "mysql.railway.internal",
      DB_PORT: "3306",
      DB_NAME: "railway",
      DB_USER: "root",
      REDIS_URL: "redis://redis.railway.internal:6379",
      REDIS_REQUIRED: "true",
      JWT_ALGORITHM: "HS256",
      ACCESS_TOKEN_EXPIRE_MINUTES: "30",
      REFRESH_TOKEN_EXPIRE_DAYS: "7",
      STORAGE_BACKEND: "local",
      LOCAL_UPLOAD_DIR: "./uploads",
      CLAMAV_ENABLED: "false",
      CELERY_ENABLED: "false",
      SMTP_ENABLED: "false",
      EMAIL_ENABLED: "false",
      PROMETHEUS_METRICS_ENABLED: "false",
      ALLOWED_REDIRECT_DOMAINS: "railway.app,railway.internal",
      MFA_REQUIRED_ROLES: "SUPER_ADMIN,ADMIN",
    },
  });

  const frontend = service("frontend", {
    rootDirectory: "frontend",
    build: "docker build -f Dockerfile -t frontend .",
    start: "nginx -g 'daemon off;'",
    healthcheckPath: "/",
    env: {
      VITE_API_BASE_URL: "/api/v1",
    },
  });

  return project("CRP Production", {
    resources: [db, redis, backend, frontend],
  });
});
