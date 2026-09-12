# Cloud SQL Postgres, private-IP only. HA is a variable, not a default --
# see ADR: this was v1's unacknowledged single point of failure. Flip
# cloud_sql_high_availability to true before this holds anything real.

resource "google_sql_database_instance" "main" {
  name             = "code-kitchen-db"
  database_version = "POSTGRES_16"
  region           = var.region
  depends_on       = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = var.cloud_sql_tier
    availability_type = var.cloud_sql_high_availability ? "REGIONAL" : "ZONAL"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.cloud_sql_high_availability
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }
  }

  deletion_protection = false # flip to true outside of a lab/demo project
}

resource "google_sql_database" "app" {
  name     = "codekitchen"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "codekitchen"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
