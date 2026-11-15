# syntax=docker/dockerfile:1
# Official minio/minio and quay.io/minio/minio images no longer pull anonymously.
# This image installs the last community release that published Linux binaries:
# RELEASE.2025-09-07T16-13-09Z. Local object storage only; keep the ports on loopback.
# That release is affected by CVE-2025-62506 (service-account privilege escalation).
# This stack uses one root credential and does not create service accounts.

FROM alpine:3.22.8 AS fetch
ARG TARGETARCH
ARG MINIO_RELEASE=RELEASE.2025-09-07T16-13-09Z
WORKDIR /tmp
RUN --mount=type=cache,target=/etc/apk/cache,sharing=locked \
    apk add curl ca-certificates
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) SUM=7c5bd8512c6e966455b1d198209358b2d191c77a83ab377c4073281065fb855f ;; \
      arm64) SUM=5c83cd2cf151717ba0243f73e1c7802ff36e272b67144bdd7f1f7d684fd6f03d ;; \
      *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o minio "https://github.com/minio/minio/releases/download/${MINIO_RELEASE}/minio.linux-${TARGETARCH}.${MINIO_RELEASE}"; \
    echo "${SUM}  minio" | sha256sum -c -; \
    chmod 755 minio

FROM alpine:3.22.8 AS runtime
RUN --mount=type=cache,target=/etc/apk/cache,sharing=locked \
    apk add curl ca-certificates su-exec \
    && addgroup -S -g 1001 appgroup \
    && adduser -S -u 1001 -G appgroup -h /data appuser \
    && mkdir -p /data \
    && chown appuser:appgroup /data
COPY --from=fetch --link --chown=1001:1001 /tmp/minio /usr/local/bin/minio
COPY --link docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
ENV HOME=/data
EXPOSE 9000 9001
VOLUME /data
LABEL org.opencontainers.image.title="VisioAudit MinIO" \
      org.opencontainers.image.version="RELEASE.2025-09-07T16-13-09Z"
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["server", "/data", "--console-address", ":9001"]
