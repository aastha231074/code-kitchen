# Ingestion -> processing runs through Pub/Sub for buffering/retry/backpressure,
# with a real dead-letter topic -- v1 had none of this (direct service-to-
# service calls, no buffer, no DLQ).
#
# Note on the "Cloud Scheduler -> Pub/Sub -> Cloud Run Jobs" hop in the
# architecture diagram: Cloud Run Jobs has no native Pub/Sub trigger, so the
# Pub/Sub hop for *starting* ingestion collapses in the real implementation
# below -- Cloud Scheduler calls the Cloud Run Jobs REST API directly (see
# google_cloud_scheduler_job.ingestion_trigger). What Pub/Sub actually
# buffers is jobs-raw, immediately after ingestion -- that's the hop that
# matters for backpressure/retry, and it's unchanged from the diagram.

resource "google_pubsub_topic" "jobs_raw" {
  name = "jobs-raw"
}

resource "google_pubsub_topic" "jobs_raw_dlq" {
  name = "jobs-raw-dlq"
}

resource "google_pubsub_subscription" "jobs_raw_push" {
  name  = "jobs-raw-process-worker-push"
  topic = google_pubsub_topic.jobs_raw.name

  push_config {
    push_endpoint = google_cloud_run_v2_service.process_worker.uri
    oidc_token {
      service_account_email = google_service_account.process_worker.email
    }
  }

  ack_deadline_seconds = 30

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.jobs_raw_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "60s"
  }
}

resource "google_pubsub_subscription" "jobs_raw_dlq_pull" {
  name  = "jobs-raw-dlq-pull"
  topic = google_pubsub_topic.jobs_raw_dlq.name
  # Pulled by an on-call/ops process or a small alerting job -- not wired to
  # an automated handler here since DLQ triage is inherently a human step.
}

resource "google_cloud_scheduler_job" "ingest_indeed_trigger" {
  name      = "code-kitchen-ingest-indeed-trigger"
  schedule  = "0 */4 * * *" # every 4 hours
  time_zone = "Etc/UTC"

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.ingest_indeed.name}:run"
    http_method = "POST"
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

resource "google_service_account" "scheduler" {
  account_id   = "code-kitchen-scheduler"
  display_name = "Code Kitchen -- Cloud Scheduler (triggers ingestion jobs only)"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_can_run_ingest_indeed" {
  name     = google_cloud_run_v2_job.ingest_indeed.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
