# Secret Manager holds credentials. Access is granted per-service below in
# iam.tf -- e.g. only ingest-indeed can read the Indeed key; ai-api never
# sees scraping credentials, and vice versa (least privilege, ADR pattern).

resource "google_secret_manager_secret" "db_password" {
  secret_id = "code-kitchen-db-password"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "code-kitchen-gemini-api-key"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key != "" ? var.gemini_api_key : "unset"
}

resource "google_secret_manager_secret" "indeed_api_key" {
  secret_id = "code-kitchen-indeed-api-key"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "indeed_api_key" {
  secret      = google_secret_manager_secret.indeed_api_key.id
  secret_data = var.indeed_api_key != "" ? var.indeed_api_key : "unset"
}
