FROM python:3.12-slim
WORKDIR /app

COPY services/process_worker/requirements.txt /app/services/process_worker/requirements.txt
RUN pip install --no-cache-dir -r /app/services/process_worker/requirements.txt

COPY services/common /app/services/common
COPY services/process_worker /app/services/process_worker
COPY services/__init__.py /app/services/__init__.py

ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["uvicorn", "services.process_worker.main:app", "--host", "0.0.0.0", "--port", "8080"]
