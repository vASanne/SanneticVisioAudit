# syntax=docker/dockerfile:1

FROM node:22.23.5-bookworm-slim AS deps
WORKDIR /src
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=secret,id=npmrc,target=/root/.npmrc,required=false \
    --mount=type=cache,target=/root/.npm \
    npm ci

FROM deps AS dev
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY docker-entrypoint.dev.sh /usr/local/bin/docker-entrypoint.dev.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.dev.sh
COPY . .
EXPOSE 3000
# Dev stage only. The runtime stage below sets USER appuser.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.dev.sh"]

FROM deps AS build
ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
COPY . .
RUN npm run build

FROM node:22.23.5-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser
COPY --from=build --link --chown=1001:1001 /src/.next/standalone ./
COPY --from=build --link --chown=1001:1001 /src/.next/static ./.next/static
COPY --from=build --link --chown=1001:1001 /src/public ./public
COPY --link --chown=1001:1001 trust-proxy.cjs ./trust-proxy.cjs
USER appuser
EXPOSE 3000
LABEL org.opencontainers.image.title="Sannetic Vision Audit Web"
ENTRYPOINT ["node", "server.js"]
