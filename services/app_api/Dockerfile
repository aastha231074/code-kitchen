FROM python:3.12-slim
WORKDIR /app

COPY services/app_api/requirements.txt /app/services/app_api/requirements.txt
RUN pip install --no-cache-dir -r /app/services/app_api/requirements.txt

COPY services/common /app/services/common
COPY services/app_api /app/services/app_api
COPY services/__init__.py /app/services/__init__.py

ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["uvicorn", "services.app_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
