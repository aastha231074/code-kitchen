variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "Primary region for Cloud Run, Cloud SQL, and Pub/Sub resources."
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "Password for the codekitchen Postgres user. Pass via TF_VAR_db_password, never commit it."
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key, stored in Secret Manager. Leave empty to deploy with USE_MOCK_AI=true."
  type        = string
  sensitive   = true
  default     = ""
}

variable "indeed_publisher_id" {
  type    = string
  default = ""
}

variable "indeed_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "enable_linkedin_scrape" {
  description = "Leave false. Flip only after an explicit legal risk-acceptance sign-off (see architecture report, section 7) -- LinkedIn's ToS prohibits scraping."
  type        = bool
  default     = false
}

variable "container_image_tag" {
  description = "Tag applied to all service images in Artifact Registry (e.g. a git SHA)."
  type        = string
  default     = "latest"
}

variable "cloud_sql_tier" {
  description = "Machine tier for Cloud SQL. db-f1-micro is fine for a lab/demo; use HA + a larger tier for anything real."
  type        = string
  default     = "db-f1-micro"
}

variable "cloud_sql_high_availability" {
  description = "Regional HA failover for Cloud SQL. Off by default to fit lab quota; turn on before this holds real user data."
  type        = bool
  default     = false
}
