FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN useradd --create-home --uid 10001 praetor

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    pyyaml \
    httpx \
    itsdangerous \
    jinja2 \
    python-multipart

COPY apps/api /app/apps/api
COPY workers/runtime /app/workers/runtime
RUN mkdir -p /app/data /app/workspace /app/config && chown -R praetor:praetor /app

ENV PRAETOR_STATE_DIR=/app/data/state
USER praetor

CMD ["python", "-m", "uvicorn", "--app-dir", "/app/apps/api", "praetor_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
