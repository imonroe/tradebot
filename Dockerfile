FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY src/ src/
COPY config/ config/

# Install dependencies
RUN uv pip install --system .

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV TRADEBOT_DATABASE_URL=sqlite:////app/data/tradebot.db

EXPOSE 8000

CMD ["python", "-m", "tradebot.main"]
