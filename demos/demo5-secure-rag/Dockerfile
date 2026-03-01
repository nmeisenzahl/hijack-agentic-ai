FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml README.md ./
COPY src/ src/

RUN uv sync

CMD ["uv", "run", "python", "-m", "src.main"]
