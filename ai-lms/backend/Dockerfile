# Build context is the ai-lms folder:  docker build -f backend/Dockerfile .
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --require-hashes -r requirements.txt

COPY backend/ ./
COPY sample-data/ ./sample-data/

RUN useradd --system --uid 10001 --home-dir /app ailms
USER ailms

EXPOSE 8000

# Prepare the database and sample data, then serve. The worker overrides this command.
CMD ["sh", "-c", "python -m ailms.bootstrap && exec uvicorn ailms.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
