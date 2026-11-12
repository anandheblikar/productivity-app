# How to build the app into a container image for hosting (Render reads this).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Bring in uv (our package manager) from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install just the runtime dependencies first (cached unless they change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Then copy the app code.
COPY . .

# The host sets $PORT; default to 8000 locally. Bind to 0.0.0.0 so it's
# reachable from outside the container. Run the uvicorn installed in the
# project's virtual environment (no dependency re-check at startup).
CMD ["sh", "-c", ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
