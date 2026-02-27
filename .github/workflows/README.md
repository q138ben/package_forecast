# GitHub Actions Workflows

This directory contains all CI/CD workflow definitions for the Package Forecast project with comprehensive MLOps capabilities.

## Workflows Overview

### 1. Main CI/CD Pipeline (`ci-cd.yml`)
**Purpose:** Main continuous integration and deployment pipeline

**Triggers:** Push to main/develop, PRs to main, manual dispatch

**Jobs:**
1. `validate-data` - Validate data quality
2. `test` - Run tests and linting
3. `train-models` - Train forecasting models
4. `build-and-push` - Build Docker image
5. `deploy` - Deploy to Cloud Run
6. `post-deployment` - Cleanup and tagging

### 2. Data Validation (`data-validation.yml`)
**Purpose:** Automated data quality checks

**Triggers:** Daily at 2 AM UTC, manual, data file changes

**Features:** Schema validation, quality checks, profiling

### 3. Model Training (`model-training.yml`)
**Purpose:** Train and evaluate forecasting models

**Triggers:** Weekly on Sundays at 3 AM UTC, manual

**Features:** Version generation, training, evaluation, threshold checking, GCS upload

### 4. Artifact Management (`artifact-management.yml`)
**Purpose:** Manage model versions and artifacts

**Actions:** list-versions, promote-to-production, rollback, cleanup-old

### 5. Monitoring (`monitoring.yml`)
**Purpose:** Monitor service health and performance

**Triggers:** Every 6 hours, manual

**Features:** Health checks, performance monitoring, drift detection, alerting

## Setup Required

### GitHub Secrets
1. **GCP_PROJECT_ID** - Your Google Cloud project ID
2. **GCP_SA_KEY** - Service account JSON key

### Service Account Permissions
- Cloud Run Admin
- Cloud Build Editor
- Storage Admin
- Service Account User
- Monitoring Viewer

## Usage Examples

```bash
# Trigger training
gh workflow run model-training.yml

# Promote model
gh workflow run artifact-management.yml \
  -f action=promote-to-production \
  -f version=v20260227-143052-abc123d

# Rollback
gh workflow run artifact-management.yml \
  -f action=rollback \
  -f version=v20260220-120000-xyz789d
```

## Documentation

See comprehensive guides:
- `docs/CICD_GUIDE.md` - Full documentation
- `docs/CICD_QUICK_REFERENCE.md` - Quick commands
- `docs/CICD_ARCHITECTURE.md` - Architecture diagrams
- `SETUP_CHECKLIST.md` - Setup checklist
