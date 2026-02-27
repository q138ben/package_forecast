# CI/CD Quick Reference

## Initial Setup

### Configure Environment
```bash
# Copy and edit .env file
cp .env.example .env

# Edit .env and set your GCP_PROJECT_ID
nano .env  # or use your favorite editor
```

## Workflows

### Trigger Training Manually
```bash
gh workflow run model-training.yml
```

### Trigger with Custom Version
```bash
gh workflow run model-training.yml -f model_version=v1.0.0
```

### Deploy to Staging
```bash
# Make sure .env is configured with GCP_PROJECT_ID
./scripts/deploy.sh staging
```

### Deploy to Production
```bash
# Make sure .env is configured with GCP_PROJECT_ID
./scripts/deploy.sh production
```

### Promote Model to Production
```bash
gh workflow run artifact-management.yml \
  -f action=promote-to-production \
  -f version=v20260227-143052-abc123d
```

### Rollback Deployment
```bash
gh workflow run artifact-management.yml \
  -f action=rollback \
  -f version=v20260227-120000-xyz789d
``` (reads from .env):
```bash
./scripts/rollback.sh production
```bash
./scripts/rollback.sh production $GCP_PROJECT_ID
```

### List Model Versions
```bash
gh workflow run artifact-management.yml -f action=list-versions
```

### Cleanup Old Artifacts
```bash
gh workflow run artifact-management.yml -f action=cleanup-old
```

## Local Commands

### Validate Data
```bash
python scripts/validate_data.py --input data-4-.csv --output validation-report.json
```

### Profile Data
```bash
python scripts/profile_data.py --input data-4-.csv --output data-profile.html
```

### Train Models
```bash
python main.py train --data-path data-4-.csv --artifacts-dir artifacts
```

### Generate Forecasts
```bash
python main.py forecast --artifacts-dir artifacts
```

### Extract Metrics
```bash
python scripts/extract_metrics.py --artifacts-dir artifacts --output metrics-summary.json
```

### Evaluate Models
```bash
python scripts/evaluate_models.py --artifacts-dir artifacts --output evaluation-report.json
```

### Generate Evaluation Plots
```bash
python scripts/generate_evaluation_plots.py --artifacts-dir artifacts --output evaluation-plots/
```

### Check Performance Thresholds
```bash
python scripts/check_thresholds.py \
  --metrics evaluation-report.json \
  --thresholds config/model-thresholds.yml
```

### Check Model Drift
```bash
python scripts/check_model_drift.py --artifacts-dir artifacts --output drift-report.json
```

### Register Model
```bash
python scripts/register_model.py \
  --version v1.0.0 \
  --metrics metrics-summary.json \
  --artifacts-dir artifacts \
  --git-commit $(git rev-parse HEAD) \
  --output model-registry.json
```

## Testing Deployed Service

### Health Check
```bash
curl https://your-service-url.run.app/health
```

### Ready Check
```bash
curl https://your-service-url.run.app/ready
```

### Get Forecast
```bash
curl https://your-service-url.run.app/forecast/A
curl https://your-service-url.run.app/forecast/B
curl https://your-service-url.run.app/forecast/C
```

### Get All Forecasts
```bash
curl https://your-service-url.run.app/
```

## GCS Commands

### List Model Versions
```bash
gsutil ls gs://package-forecast-artifacts/
```

### Download Model Artifacts
```bash
gsutil -m cp -r gs://package-forecast-artifacts/v20260227-143052-abc123d/ ./local-artifacts/
```

### Check Latest Version
```bash
gsutil cat gs://package-forecast-artifacts/latest-version.txt
```

### Check Production Version
```bash
gsutil cat gs://package-forecast-artifacts/production-version.txt
```

## Cloud Run Commands

### Get Service URL
```bash
gcloud run services describe package-forecast \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

### List Revisions
```bash
gcloud run revisions list \
  --service package-forecast \
  --region us-central1
```

### View Logs
```bash
gcloud run services logs read package-forecast \
  --region us-central1 \
  --limit 50
```

### Update Traffic Split
```bash
gcloud run services update-traffic package-forecast \
  --to-revisions=REVISION_NAME=100 \
  --region us-central1
```

## Monitoring

### View Recent Workflow Runs
```bash
gh run list --workflow=ci-cd.yml --limit 10
```

### View Workflow Run Details
```bash
gh run view <run-id>
```

### Download Workflow Artifacts
```bash
gh run download <run-id>
```

### View Service Metrics (GCP Console)
```
https://console.cloud.google.com/run/detail/us-central1/package-forecast/metrics
```

## Git Commands

### List Deployment Tags
```bash
git tag | grep deploy-
```

### List Production Tags
```bash
git tag | grep prod-
```

### View Tag Details
```bash
git show deploy-20260227-143052
```

## Troubleshooting

### View GitHub Actions Logs
```bash
gh run view <run-id> --log
```

### Re-run Failed Workflow
```bash
gh run rerun <run-id>
```

### Cancel Running Workflow
```bash
gh run cancel <run-id>
```

### Check Cloud Run Service Status
```bash
gcloud run services describe package-forecast \
  --region us-central1 \
  --format json
```

### Check Container Registry Images
```bash
gcloud container images list --repository gcr.io/$GCP_PROJECT_ID
```

### Delete Old Container Images
```bash
gcloud container images list-tags gcr.io/$GCP_PROJECT_ID/package-forecast \
  --format="get(digest)" --filter="timestamp.datetime<$(date -d '30 days ago' --iso-8601)" | \
  xargs -I {} gcloud container images delete "gcr.io/$GCP_PROJECT_ID/package-forecast@{}" --quiet
```

## Environment Variables

Configuration is stored in `.env` file (not committed to git):
```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env

# Set required variables:
# - GCP_PROJECT_ID (required)
# - GCP_REGION (optional, defaults to us-central1)
# - CLOUD_RUN_SERVICE_NAME (optional)
# - And others as needed

# Verify configuration loads
python -c "from src.config import get_project_config; print(get_project_config())"
```

See `docs/ENVIRONMENT_CONFIGURATION.md` for complete reference.

## Required Permissions

Service account needs:
- Cloud Run Admin
- Cloud Build Editor  
- Storage Admin
- Service Usage Consumer
- Monitoring Viewer
- Logs Writer

## Pipeline Status

Check pipeline status:
```bash
# Overall CI/CD status
gh run list --workflow=ci-cd.yml --limit 1

# Training status
gh run list --workflow=model-training.yml --limit 1

# Monitoring status
gh run list --workflow=monitoring.yml --limit 1
```

## Common Workflows

### Full Model Update
```bash
# 1. Validate data
python scripts/validate_data.py --input data-4-.csv

# 2. Train models
python main.py train

# 3. Evaluate
python scripts/evaluate_models.py --artifacts-dir artifacts

# 4. Check thresholds
python scripts/check_thresholds.py \
  --metrics evaluation-report.json \
  --thresholds config/model-thresholds.yml

# 5. Generate version
VERSION="v$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"

# 6. Register model
python scripts/register_model.py \
  --version $VERSION \
  --metrics metrics-summary.json \
  --artifacts-dir artifacts \
  --git-commit $(git rev-parse HEAD)

# 7. Deploy
./scripts/deploy.sh production
```

### Emergency Rollback
```bash
# 1. Check current production version
gsutil cat gs://package-forecast-artifacts/production-version.txt

# 2. List available versions
gsutil ls gs://package-forecast-artifacts/ | grep v20

# 3. Rollback (uses .env for project configuration)
./scripts/rollback.sh production

# 4. Verify
curl https://your-service-url.run.app/health
```
