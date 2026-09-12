#!/usr/bin/env bash
# Builds every service image, pushes to Artifact Registry, applies the
# Terraform stack, and runs DB migrations against the new Cloud SQL
# instance. Meant for a real/persistent GCP project -- a 6-day qwiklabs
# sandbox may not have quota/time for the full VPC peering + Cloud SQL
# provisioning path below; docker-compose is the faster path to a working
# demo inside a short-lived lab.
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_REGION:=us-central1}"
: "${TF_VAR_db_password:?Set TF_VAR_db_password}"

TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
REPO="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/code-kitchen"

echo "==> Configuring gcloud + docker auth"
gcloud config set project "$GCP_PROJECT_ID"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

echo "==> Applying Terraform (creates the Artifact Registry repo first)"
pushd infra/terraform >/dev/null
terraform init -upgrade
terraform apply -target=google_artifact_registry_repository.images \
  -var="project_id=${GCP_PROJECT_ID}" -var="region=${GCP_REGION}" -auto-approve
popd >/dev/null

echo "==> Building and pushing images (tag: ${TAG})"
for svc in ingest_indeed ingest_linkedin process_worker ai_api referral_api app_api; do
  name=$(echo "$svc" | tr '_' '-')
  docker build -t "${REPO}/${name}:${TAG}" -f "services/${svc}/Dockerfile" .
  docker push "${REPO}/${name}:${TAG}"
done
docker build -t "${REPO}/web:${TAG}" -f web/Dockerfile .
docker push "${REPO}/web:${TAG}"

echo "==> Applying full Terraform stack"
pushd infra/terraform >/dev/null
terraform apply \
  -var="project_id=${GCP_PROJECT_ID}" \
  -var="region=${GCP_REGION}" \
  -var="container_image_tag=${TAG}" \
  -auto-approve
DB_IP=$(terraform output -raw db_private_ip)
APP_API_URL=$(terraform output -raw app_api_url)
popd >/dev/null

echo "==> Running DB migrations against ${DB_IP} (requires network access to the private IP, e.g. via a bastion or Cloud SQL Auth Proxy)"
for f in db/migrations/*.sql; do
  echo "  applying $f"
  PGPASSWORD="$TF_VAR_db_password" psql "host=${DB_IP} dbname=codekitchen user=codekitchen sslmode=require" -f "$f"
done

echo "==> Done. app-api is live at: ${APP_API_URL}"
echo "    Point web/config.js's APP_API_BASE at that URL and redeploy the web image, or serve web/ separately."
