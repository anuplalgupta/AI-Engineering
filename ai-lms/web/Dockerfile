# syntax=docker/dockerfile:1.7
# Stage 1: build the static app. The output is plain files, so it is built on the
# builder's own platform and copied into a Caddy image for linux/amd64 or linux/arm64.
FROM --platform=$BUILDPLATFORM node:20.18.1-alpine3.20 AS build
WORKDIR /app
ENV CI=true NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false
COPY package.json package-lock.json ./
# Optional build secret "extra_ca": a company proxy's root certificate, added to
# the trusted list for this step only (certificates are still verified).
RUN --mount=type=secret,id=extra_ca,required=false     if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi;     npm ci --no-audit
COPY . .
RUN npm run build

# Stage 2: Caddy serves the built files and passes /api to the backend.
FROM caddy:2.8.4-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:80/healthz || exit 1
