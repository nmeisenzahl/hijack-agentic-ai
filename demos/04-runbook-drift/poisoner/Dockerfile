FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app
COPY send.py .

USER app
CMD ["python", "send.py"]
