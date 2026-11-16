# Stage 1: build the static app.
FROM node:20.18.1-alpine3.20 AS build
WORKDIR /app
ENV CI=true NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false
COPY package.json package-lock.json ./
RUN npm ci --no-audit
COPY . .
RUN npm run build

# Stage 2: Caddy serves the built files and passes /api to the backend.
FROM caddy:2.8.4-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:80/healthz || exit 1
