# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_APP_URL
ENV NEXT_PUBLIC_APP_URL=${NEXT_PUBLIC_APP_URL}
# Next.js bakes rewrite destinations into the build output, so the internal API address
# must be known at build time (it is the compose service name, reachable inside Docker).
ARG INTERNAL_API_URL=http://backend-api:8000
ENV INTERNAL_API_URL=${INTERNAL_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 INTERNAL_API_URL=http://backend-api:8000
RUN addgroup -S -g 10001 vimora && adduser -S -u 10001 -G vimora vimora
COPY --from=build --chown=vimora:vimora /app/.next/standalone ./
COPY --from=build --chown=vimora:vimora /app/.next/static ./.next/static
COPY --from=build --chown=vimora:vimora /app/public ./public
USER vimora
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD wget -qO- http://127.0.0.1:3000/robots.txt >/dev/null || exit 1
CMD ["node", "server.js"]
