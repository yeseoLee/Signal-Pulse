FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY config ./config
COPY src ./src

RUN uv sync --no-dev

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "watchlist_signal_bot.main", "--dry-run"]
