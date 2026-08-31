FROM python:3.12-slim

ENV HOME=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONWARNINGS="ignore::DeprecationWarning,ignore::UserWarning"

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# The agent modules import each other as `agent.*`, so keep the package layout.
COPY --chown=app:app . agent/
RUN pip install --no-cache-dir -e ./agent \
    && chown -R app:app /app

USER app

CMD ["python", "-m", "agent.main"]
