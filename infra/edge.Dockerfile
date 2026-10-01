# The platform owns the single Edge implementation and shared IoT contract.
ARG PYTHON_IMAGE=python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.17@sha256:03bdc89bb9798628846e60c3a9ad19006c8c3c724ccd2985a33145c039a0577b
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE}
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY packages/iot-contract /app/packages/iot-contract
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca,target=/tmp/build-ca.pem \
    if [ -f /tmp/build-ca.pem ]; then export SSL_CERT_FILE=/tmp/build-ca.pem; fi; \
    uv venv --python /usr/local/bin/python /app/.venv && \
    uv sync --locked --only-group edge && \
    groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app && \
    mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 edge/*.py /app/edge/
COPY --chown=10001:10001 edge/tools/status.py edge/tools/migrate_legacy.py /app/edge/tools/
COPY --chown=10001:10001 infra/container-entrypoint.py /app/container-entrypoint.py
WORKDIR /app/edge
USER 10001:10001
ENTRYPOINT ["python", "/app/container-entrypoint.py"]
