# Docker Official Image mirrored on Amazon ECR Public.
FROM public.ecr.aws/docker/library/python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --timeout 90 --disable-pip-version-check -r requirements.txt

FROM public.ecr.aws/docker/library/python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system agent && useradd --system --gid agent agent
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app/ app/
COPY utils/ utils/
USER agent

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + (os.getenv('PORT') or '8000') + '/health', timeout=2)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
