# One service account per service, scoped to only what it touches -- the
# least-privilege pattern called out across the architecture report.

resource "google_service_account" "ingest_indeed" {
  account_id   = "ck-ingest-indeed"
  display_name = "Code Kitchen -- ingest-indeed job"
}
resource "google_service_account" "ingest_linkedin" {
  account_id   = "ck-ingest-linkedin"
  display_name = "Code Kitchen -- ingest-linkedin job (ToS-risk fallback, gated)"
}
resource "google_service_account" "process_worker" {
  account_id   = "ck-process-worker"
  display_name = "Code Kitchen -- process-worker"
}
resource "google_service_account" "ai_api" {
  account_id   = "ck-ai-api"
  display_name = "Code Kitchen -- ai-api"
}
resource "google_service_account" "referral_api" {
  account_id   = "ck-referral-api"
  display_name = "Code Kitchen -- referral-api"
}
resource "google_service_account" "app_api" {
  account_id   = "ck-app-api"
  display_name = "Code Kitchen -- app-api (BFF)"
}

# --- Secret access: only ingestion touches scraping/API credentials ---
resource "google_secret_manager_secret_iam_member" "indeed_key_for_ingest" {
  secret_id = google_secret_manager_secret.indeed_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingest_indeed.email}"
}
resource "google_secret_manager_secret_iam_member" "gemini_key_for_process_worker" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.process_worker.email}"
}
resource "google_secret_manager_secret_iam_member" "gemini_key_for_ai_api" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ai_api.email}"
}

# --- DB access: every backend service, not the ingestion jobs (they only
# publish to Pub/Sub and write to Cloud Storage -- see storage.tf) ---
locals {
  db_client_sas = [
    google_service_account.process_worker.email,
    google_service_account.ai_api.email,
    google_service_account.referral_api.email,
    google_service_account.app_api.email,
  ]
}
resource "google_secret_manager_secret_iam_member" "db_password_for_backend" {
  for_each  = toset(local.db_client_sas)
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}
resource "google_project_iam_member" "cloudsql_client" {
  for_each = toset(local.db_client_sas)
  project  = var.project_id
  role     = "roles/cloudsql.client"
  member   = "serviceAccount:${each.value}"
}

# --- Storage: only ingestion writes raw postings; only ai-api writes resumes ---
resource "google_storage_bucket_iam_member" "raw_jobs_writer" {
  bucket = google_storage_bucket.raw_jobs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingest_indeed.email}"
}
resource "google_storage_bucket_iam_member" "resumes_writer" {
  bucket = google_storage_bucket.resumes.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ai_api.email}"
}

# --- Pub/Sub: ingestion publishes, process-worker's push subscription is
# invoked via OIDC (see pubsub.tf) ---
resource "google_pubsub_topic_iam_member" "ingest_indeed_publisher" {
  topic  = google_pubsub_topic.jobs_raw.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.ingest_indeed.email}"
}

# --- Vertex AI (embeddings + Gemini): process-worker embeds, ai-api ranks/generates ---
resource "google_project_iam_member" "vertex_ai_process_worker" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.process_worker.email}"
}
resource "google_project_iam_member" "vertex_ai_ai_api" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ai_api.email}"
}

# --- app-api is the only caller of ai-api / referral-api's HTTP endpoints ---
resource "google_cloud_run_v2_service_iam_member" "app_api_invokes_ai_api" {
  name     = google_cloud_run_v2_service.ai_api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app_api.email}"
}
resource "google_cloud_run_v2_service_iam_member" "app_api_invokes_referral_api" {
  name     = google_cloud_run_v2_service.referral_api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app_api.email}"
}
