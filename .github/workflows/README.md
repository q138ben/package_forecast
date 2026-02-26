# GitHub Actions CI/CD Pipeline

This directory contains automated workflows for testing and deployment.

## Workflow: ci-cd.yml

### Triggers
- **Pull Requests**: Runs tests on all PRs to `main`
- **Push to main**: Runs tests + deploys to Google Cloud Run

### Jobs

#### 1. Test Job
Runs on every push and PR:
- Linting with `ruff`
- Unit tests with `pytest`
- Code coverage reporting
- Local API testing

#### 2. Deploy Job
Runs only on pushes to `main`:
- Authenticates to Google Cloud
- Builds Docker image using Cloud Build
- Deploys to Cloud Run
- Verifies deployment with health checks

## Setup Required

### GitHub Secrets
Add these secrets to your GitHub repository (Settings → Secrets → Actions):

1. **GCP_PROJECT_ID**: Your Google Cloud project ID
   ```
   example-project-123456
   ```

2. **GCP_SA_KEY**: Service account JSON key with permissions:
   - Cloud Build Editor
   - Cloud Run Admin
   - Service Account User
   - Storage Admin

   To create the service account key:
   ```bash
   # Create service account
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions"
   
   # Grant permissions
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/cloudbuild.builds.editor"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   
   # Create and download key
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@PROJECT_ID.iam.gserviceaccount.com
   
   # Copy the contents of key.json and add as GCP_SA_KEY secret
   ```

## Local Testing

Test the workflow locally before pushing:
```bash
# Run tests
pytest --cov=src --cov-report=term-missing

# Run linting
ruff check src/

# Test forecasts
python main.py forecast --location A
python main.py forecast --location B
python main.py forecast --location C
```

## Deployment Flow

1. Developer pushes code or creates PR
2. GitHub Actions triggers test job
3. If tests pass and push is to `main`, deploy job triggers
4. Docker image is built and pushed to GCR
5. Cloud Run service is updated
6. Health checks verify deployment
7. Service URL is displayed in logs
