"""File storage: local disk for docker-compose dev, GCS on Cloud Run.
Same interface either way so service code never branches on environment.
"""
import os

from .config import settings


def write_bytes(path: str, data: bytes) -> str:
    """path is a relative key, e.g. 'raw-jobs/indeed/2026-09-12/abc123.json'."""
    if settings.storage_backend == "gcs":
        from google.cloud import storage

        bucket_name = settings.gcs_bucket_raw_jobs if path.startswith("raw-jobs/") else settings.gcs_bucket_resumes
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        blob.upload_from_string(data)
        return f"gs://{bucket_name}/{path}"

    full_path = os.path.join(settings.local_storage_root, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(data)
    return full_path


def read_bytes(ref: str) -> bytes:
    if ref.startswith("gs://"):
        from google.cloud import storage

        _, _, rest = ref.partition("gs://")
        bucket_name, _, path = rest.partition("/")
        client = storage.Client()
        return client.bucket(bucket_name).blob(path).download_as_bytes()

    with open(ref, "rb") as f:
        return f.read()
