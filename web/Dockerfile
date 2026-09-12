FROM python:3.12-slim
WORKDIR /site
COPY web/ /site/
EXPOSE 8090
CMD ["python", "-m", "http.server", "8090"]
