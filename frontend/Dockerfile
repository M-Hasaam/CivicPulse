# syntax=docker/dockerfile:1

# Base pinned by digest: the same bytes on every laptop and CI runner.
ARG NODE_IMAGE=node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.29-alpine@sha256:0c79d56aee561a1d81c63f00eee5fb5fe29279560cdc55e91425133104c7fbe6

# --- builder: compile the Vite/React app to static assets -----------------------------
FROM ${NODE_IMAGE} AS builder

WORKDIR /build
# Dependencies first: this layer is rebuilt only when the lockfile changes, not on
# every source edit. npm ci (not install) so it fails on a lockfile mismatch instead
# of silently resolving new versions.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- runtime: nginx serving the built assets, already non-root ------------------------
# nginxinc/nginx-unprivileged listens on 8080 and runs as the unprivileged 'nginx'
# user out of the box - no USER directive or permission juggling needed here.
FROM ${NGINX_IMAGE}

USER root
RUN apk upgrade --no-cache
USER nginx

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/"]
