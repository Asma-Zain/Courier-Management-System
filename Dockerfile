# ---- build stage: install pinned dependencies into a virtualenv
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# ---- runtime stage: slim, non-root, no secrets baked in (env vars come from the compose env file)
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH" APP_ENV=production
RUN useradd --system --uid 10001 --no-create-home parcelly
WORKDIR /srv
COPY --from=build /opt/venv /opt/venv
COPY backend backend
COPY static static
USER parcelly
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8000'), timeout=4).status == 200 else 1)"
# One process on purpose: the in-memory rate limiter is per process. Hosts like Render set PORT.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
