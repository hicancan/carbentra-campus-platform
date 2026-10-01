ARG API_IMAGE=carbentra-campus-api:local
FROM ${API_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --group edge --group dev
COPY edge /app/edge
ENV PYTHONPATH=/app/backend
WORKDIR /app/edge
USER 10001:10001
CMD ["python", "-m", "pytest", "tests", "-r", "s", "-o", "cache_dir=/tmp/pytest-cache"]
