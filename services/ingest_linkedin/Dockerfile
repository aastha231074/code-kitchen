FROM python:3.12-slim
WORKDIR /app

COPY services/ingest_linkedin/requirements.txt /app/services/ingest_linkedin/requirements.txt
RUN pip install --no-cache-dir -r /app/services/ingest_linkedin/requirements.txt

COPY services/common /app/services/common
COPY services/ingest_linkedin /app/services/ingest_linkedin
COPY services/__init__.py /app/services/__init__.py

ENV PYTHONPATH=/app
CMD ["python", "-m", "services.ingest_linkedin.main"]
