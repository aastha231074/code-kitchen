output "app_api_url" {
  value = google_cloud_run_v2_service.app_api.uri
}

output "db_private_ip" {
  value = google_sql_database_instance.main.private_ip_address
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "raw_jobs_bucket" {
  value = google_storage_bucket.raw_jobs.name
}

output "resumes_bucket" {
  value = google_storage_bucket.resumes.name
}
