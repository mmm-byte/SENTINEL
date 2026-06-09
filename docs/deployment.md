SENTINEL Deployment — Cloud Run + Workload Identity
===================================================

This document shows a minimal, secure deployment pattern for the SENTINEL
orchestrator and gateway on Google Cloud Run using Workload Identity and
Secret Manager.

Prerequisites
- Google Cloud project and billing enabled
- `gcloud` CLI installed and authenticated
- Google Cloud SDK components: `gcloud`, `gcloud auth`, `gcloud iam`, `gcloud run`

High-level architecture
- `orchestrator` container: runs the central controller (the healing loop)
- `gateway` container: authenticates/forwards outbound MCP calls
- Mocks or partner adapters run as separate services or external endpoints

1) Build container images
```bash
# from repo root
docker build -t gcr.io/$PROJECT/sentinel-orchestrator:latest -f Dockerfile .
docker build -t gcr.io/$PROJECT/sentinel-gateway:latest -f agent/gateway/Dockerfile .
# push to Container Registry or Artifact Registry
docker push gcr.io/$PROJECT/sentinel-orchestrator:latest
docker push gcr.io/$PROJECT/sentinel-gateway:latest
```

2) Create service accounts & Workload Identity
```bash
# create SA for orchestrator
gcloud iam service-accounts create sentinel-orch-sa --project=$PROJECT
# grant needed roles (Secret Manager access, logging, etc.)
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:sentinel-orch-sa@$PROJECT.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"

# create a KSA (if using GKE) or allow Cloud Run to impersonate
# For Cloud Run, deploy the service with --service-account=sentinel-orch-sa@$PROJECT.iam.gserviceaccount.com
```

3) Store secrets
```bash
gcloud secrets create SENTINEL_MCP_SIGNING_KEY --data-file=<(echo -n "<hmac-secret>")
gcloud secrets add-iam-policy-binding SENTINEL_MCP_SIGNING_KEY --member="serviceAccount:sentinel-orch-sa@$PROJECT.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

4) Deploy to Cloud Run
```bash
gcloud run deploy sentinel-orchestrator \
  --image gcr.io/$PROJECT/sentinel-orchestrator:latest \
  --region us-central1 \
  --platform managed \
  --service-account sentinel-orch-sa@$PROJECT.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT,AUTO_APPROVE_SCHEMA_CHANGES=false \
  --allow-unauthenticated=false

gcloud run deploy sentinel-gateway \
  --image gcr.io/$PROJECT/sentinel-gateway:latest \
  --region us-central1 \
  --platform managed \
  --service-account sentinel-orch-sa@$PROJECT.iam.gserviceaccount.com
```

5) Observability & tracing
- Export OpenTelemetry traces from the app to Cloud Trace
- Send logs to Cloud Logging (structured JSON)

Notes & security
- Keep `AUTO_APPROVE_SCHEMA_CHANGES=false` in production unless you have a proven approval workflow
- Use Secret Manager for keys; do not bake secrets into images
- Consider binary attestation and signed audit logs for tamper evidence

