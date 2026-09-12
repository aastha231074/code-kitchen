resource "google_storage_bucket" "raw_jobs" {
  name     = "${var.project_id}-code-kitchen-raw-jobs"
  location = var.region

  lifecycle_rule {
    condition { age = 30 }
    action    { type = "SetStorageClass", storage_class = "NEARLINE" }
  }
  lifecycle_rule {
    condition { age = 90 }
    action    { type = "SetStorageClass", storage_class = "COLDLINE" }
  }

  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "resumes" {
  name     = "${var.project_id}-code-kitchen-resumes"
  location = var.region

  lifecycle_rule {
    condition { age = 30 }
    action    { type = "SetStorageClass", storage_class = "NEARLINE" }
  }
  lifecycle_rule {
    condition { age = 90 }
    action    { type = "SetStorageClass", storage_class = "COLDLINE" }
  }

  uniform_bucket_level_access = true
}
