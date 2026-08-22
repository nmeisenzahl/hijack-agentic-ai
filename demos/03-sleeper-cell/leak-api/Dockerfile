FROM python:3.12-slim

ENV HOME=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi==0.141.1" \
    "uvicorn==0.52.4"

COPY --chown=app:app main.py .

USER app

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
