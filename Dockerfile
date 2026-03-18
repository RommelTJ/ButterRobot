FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev
COPY app/ ./app/
EXPOSE 8585
CMD ["uv", "run", "uvicorn", "app.app:app", "--port", "8585", "--host", "0.0.0.0", "--ssl-keyfile", "/certs/key.pem", "--ssl-certfile", "/certs/cert.pem"]
