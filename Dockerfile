FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev
COPY app.py .
EXPOSE 8585
CMD ["uv", "run", "fastapi", "run", "app.py", "--port", "8585", "--host", "0.0.0.0"]
