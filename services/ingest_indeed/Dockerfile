FROM python:3.12-slim
WORKDIR /app

COPY services/ingest_indeed/requirements.txt /app/services/ingest_indeed/requirements.txt
RUN pip install --no-cache-dir -r /app/services/ingest_indeed/requirements.txt

COPY services/common /app/services/common
COPY services/ingest_indeed /app/services/ingest_indeed
COPY services/__init__.py /app/services/__init__.py
COPY scripts/seed_jobs.py /app/scripts/seed_jobs.py

ENV PYTHONPATH=/app
CMD ["python", "-m", "services.ingest_indeed.main"]
