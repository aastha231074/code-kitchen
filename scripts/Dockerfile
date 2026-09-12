FROM python:3.12-slim
WORKDIR /app

COPY scripts/requirements.txt /app/scripts/requirements.txt
RUN pip install --no-cache-dir -r /app/scripts/requirements.txt

COPY services/common /app/services/common
COPY services/__init__.py /app/services/__init__.py
COPY scripts /app/scripts

ENV PYTHONPATH=/app
CMD ["python", "scripts/bootstrap_pubsub.py"]
