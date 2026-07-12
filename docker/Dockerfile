# Multi-stage build: export locked dependencies with Poetry, install them into
# a slim runtime image. See docs/DOCKER_STRATEGY.md.

FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir poetry poetry-plugin-export
WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN poetry export --without-hashes -f requirements.txt -o requirements.txt

FROM python:3.12-slim
# libgomp1 is required by LightGBM's OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

COPY configs ./configs
COPY sql ./sql

# Data, logs, and reports are mounted volumes — never baked into the image.
VOLUME ["/app/data", "/app/logs", "/app/reports"]

ENV DEMANDPILOT_ROOT=/app
ENTRYPOINT ["demandpilot"]
CMD ["--help"]
