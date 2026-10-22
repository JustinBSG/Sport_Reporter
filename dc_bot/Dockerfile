FROM python:3.15-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-managed-python \
    && useradd --create-home appuser
COPY bot.py backend_client.py ./
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
CMD ["python", "bot.py"]
