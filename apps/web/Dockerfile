FROM node:25-slim AS frontend

WORKDIR /src/apps/web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/tsconfig.json apps/web/vite.config.ts ./
COPY apps/web/frontend ./frontend
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN useradd --create-home --uid 10001 praetor

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx

COPY apps/web /app/apps/web
COPY --from=frontend /src/apps/web/dist /app/apps/web/dist
RUN chown -R praetor:praetor /app
USER praetor

CMD ["python", "-m", "uvicorn", "--app-dir", "/app/apps/web", "praetor_web.main:app", "--host", "0.0.0.0", "--port", "3000"]
