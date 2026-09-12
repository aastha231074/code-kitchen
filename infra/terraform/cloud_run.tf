locals {
  image_repo   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
  # Reached over the private IP through the Serverless VPC Access connector
  # (see networking.tf) -- no Cloud SQL Auth Proxy sidecar needed since the
  # instance has no public IP and Cloud Run is on the same private network.
  database_url = "postgresql://codekitchen:${var.db_password}@${google_sql_database_instance.main.private_ip_address}:5432/codekitchen"

  common_env = [
    { name = "DATABASE_URL", value = local.database_url },
    { name = "PUBSUB_PROJECT_ID", value = var.project_id },
    { name = "STORAGE_BACKEND", value = "gcs" },
    { name = "GCS_BUCKET_RAW_JOBS", value = google_storage_bucket.raw_jobs.name },
    { name = "GCS_BUCKET_RESUMES", value = google_storage_bucket.resumes.name },
    { name = "AUTH_MODE", value = "firebase" },
    { name = "FIREBASE_PROJECT_ID", value = var.project_id },
    { name = "USE_MOCK_AI", value = var.gemini_api_key == "" ? "true" : "false" },
  ]
}

# ---------------- process-worker ----------------
resource "google_cloud_run_v2_service" "process_worker" {
  name     = "process-worker"
  location = var.region

  template {
    service_account = google_service_account.process_worker.email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = "${local.image_repo}/process-worker:${var.container_image_tag}"
      dynamic "env" {
        for_each = local.common_env
        content { name = env.value.name, value = env.value.value }
      }
    }
  }
}

# ---------------- ai-api ----------------
resource "google_cloud_run_v2_service" "ai_api" {
  name     = "ai-api"
  location = var.region

  template {
    service_account = google_service_account.ai_api.email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = "${local.image_repo}/ai-api:${var.container_image_tag}"
      dynamic "env" {
        for_each = local.common_env
        content { name = env.value.name, value = env.value.value }
      }
    }
  }
}

# ---------------- referral-api ----------------
resource "google_cloud_run_v2_service" "referral_api" {
  name     = "referral-api"
  location = var.region

  template {
    service_account = google_service_account.referral_api.email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = "${local.image_repo}/referral-api:${var.container_image_tag}"
      dynamic "env" {
        for_each = local.common_env
        content { name = env.value.name, value = env.value.value }
      }
    }
  }
}

# ---------------- app-api (BFF, the only publicly invokable service) ----------------
resource "google_cloud_run_v2_service" "app_api" {
  name     = "app-api"
  location = var.region

  template {
    service_account = google_service_account.app_api.email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = "${local.image_repo}/app-api:${var.container_image_tag}"
      dynamic "env" {
        for_each = concat(local.common_env, [
          { name = "AI_API_URL", value = google_cloud_run_v2_service.ai_api.uri },
          { name = "REFERRAL_API_URL", value = google_cloud_run_v2_service.referral_api.uri },
        ])
        content { name = env.value.name, value = env.value.value }
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "app_api_public" {
  name     = google_cloud_run_v2_service.app_api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers" # app-api enforces its own per-request Firebase auth; see services/common/auth.py
}

# ---------------- ingest-indeed (Cloud Run Job) ----------------
resource "google_cloud_run_v2_job" "ingest_indeed" {
  name     = "ingest-indeed"
  location = var.region

  template {
    template {
      service_account = google_service_account.ingest_indeed.email
      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image = "${local.image_repo}/ingest-indeed:${var.container_image_tag}"
        dynamic "env" {
          for_each = concat(local.common_env, [
            { name = "INDEED_PUBLISHER_ID", value = var.indeed_publisher_id },
          ])
          content { name = env.value.name, value = env.value.value }
        }
      }
      max_retries = 2
    }
  }
}

# ---------------- ingest-linkedin (Cloud Run Job, gated fallback) ----------------
resource "google_cloud_run_v2_job" "ingest_linkedin" {
  name     = "ingest-linkedin"
  location = var.region

  template {
    template {
      service_account = google_service_account.ingest_linkedin.email
      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image = "${local.image_repo}/ingest-linkedin:${var.container_image_tag}"
        dynamic "env" {
          for_each = concat(local.common_env, [
            { name = "ENABLE_LINKEDIN_SCRAPE", value = tostring(var.enable_linkedin_scrape) },
          ])
          content { name = env.value.name, value = env.value.value }
        }
      }
      max_retries = 0
    }
  }
}
