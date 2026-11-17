# syntax=docker/dockerfile:1.7
# Build context is the ai-lms folder:  docker build -f backend/Dockerfile .
FROM python:3.12.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY backend/requirements.txt ./
# On a network that inspects HTTPS (a company proxy), pass the proxy's root
# certificate as the optional build secret "extra_ca". Certificates are still
# verified; the extra one is only added to the trusted list for this step.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca.pem; \
      export PIP_CERT=/tmp/ca.pem; \
    fi; \
    pip install --require-hashes --no-deps -r requirements.txt && rm -f /tmp/ca.pem

COPY backend/ ./
COPY sample-data/ ./sample-data/

RUN useradd --system --uid 10001 --home-dir /app ailms
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# Prepare the database and sample data, then serve. The worker overrides this command.
CMD ["sh", "-c", "python -m ailms.bootstrap && exec uvicorn ailms.main:app --host 0.0.0.0 --port 8000 --no-server-header"]
