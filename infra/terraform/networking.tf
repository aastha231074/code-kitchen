# Private VPC + Serverless VPC Access connector so Cloud Run reaches Cloud
# SQL over a private IP instead of the public internet -- see the
# architecture report's "Security & Governance" band.

resource "google_compute_network" "vpc" {
  name                    = "code-kitchen-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "code-kitchen-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "code-kitchen-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

resource "google_vpc_access_connector" "connector" {
  name          = "code-kitchen-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.10.1.0/28"
  depends_on    = [google_project_service.apis]
}
