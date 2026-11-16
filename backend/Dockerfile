# syntax=docker/dockerfile:1

FROM python:3.13.18-slim-bookworm AS build
WORKDIR /src
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=bind,source=requirements.txt,target=requirements.txt \
    --mount=type=secret,id=pip-conf,target=/etc/pip.conf,required=false \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile -r requirements.txt
COPY . .

FROM python:3.13.18-slim-bookworm AS runtime
WORKDIR /app
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser
COPY --from=build --link --chown=1001:1001 /opt/venv /opt/venv
COPY --from=build --link --chown=1001:1001 /src /app
COPY --link docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install-deps chromium \
    && playwright install chromium \
    && chown -R 1001:1001 /ms-playwright
USER appuser
EXPOSE 8000
LABEL org.opencontainers.image.title="Sannetic Vision Audit API" \
      org.opencontainers.image.description="SEO and GEO audit API"
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
