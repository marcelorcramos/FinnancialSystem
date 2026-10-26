# syntax=docker/dockerfile:1

# --- build -------------------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# --- runtime -----------------------------------------------------------------
FROM nginx:1.29-alpine

# Where nginx forwards /api. Overridable at runtime (compose, Helm).
ENV API_UPSTREAM=http://api:8000 \
    NGINX_RESOLVER=127.0.0.11

# The official image runs envsubst on /etc/nginx/templates/*.template at start.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /app/dist/finnancial-frontend/browser /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1
