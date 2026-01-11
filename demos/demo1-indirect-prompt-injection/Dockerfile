FROM python:3.11-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies
RUN uv sync

# Run the demo
CMD ["uv", "run", "python", "-m", "src.main"]
