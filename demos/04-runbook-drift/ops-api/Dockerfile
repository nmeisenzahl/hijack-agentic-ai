FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app
COPY main.py .
RUN pip install --no-cache-dir \
    fastapi==0.141.1 \
    uvicorn==0.52.4

USER app
EXPOSE 9100
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9100"]
