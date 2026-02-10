# Deployment Guide

This guide covers deploying the Package Forecast API to Google Cloud Platform (GCP) Cloud Run.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed ([Install Guide](https://cloud.google.com/sdk/docs/install))
- Docker installed locally

## Local Testing

Before deploying to the cloud, test the container locally:

```bash
# Build the Docker image
docker build -t package-forecast-api .

# Run locally
docker run -p 8000:8000 package-forecast-api

# Test
curl http://localhost:8000/health
```

## Deploy to Google Cloud Run

### 1. Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 3. Build and Push to Container Registry

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id

# Build and tag
docker build -t gcr.io/${PROJECT_ID}/package-forecast-api .

# Configure Docker for GCP
gcloud auth configure-docker

# Push to Google Container Registry
docker push gcr.io/${PROJECT_ID}/package-forecast-api
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy package-forecast-api \
  --image gcr.io/${PROJECT_ID}/package-forecast-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1
```

**Note**: Using `--allow-unauthenticated` makes the API publicly accessible. For production, remove this flag and use IAM for authentication.

### 5. Get the Service URL

```bash
gcloud run services describe package-forecast-api \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

### 6. Test the Deployed API

```bash
# Replace with your service URL
export SERVICE_URL=https://package-forecast-api-xxxxx-uc.a.run.app

curl ${SERVICE_URL}/health
curl ${SERVICE_URL}/forecast/A
```

## Alternative: One-Command Deploy

Cloud Run can build directly from source:

```bash
gcloud run deploy package-forecast-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Environment Variables (Optional)

If you need to customize the API (e.g., different model paths):

```bash
gcloud run deploy package-forecast-api \
  --image gcr.io/${PROJECT_ID}/package-forecast-api \
  --set-env-vars MODEL_DIR=/app/models
```

## Continuous Deployment with Cloud Build

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/package-forecast-api', '.']
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/package-forecast-api']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'package-forecast-api'
      - '--image=gcr.io/$PROJECT_ID/package-forecast-api'
      - '--region=us-central1'
      - '--platform=managed'

images:
  - 'gcr.io/$PROJECT_ID/package-forecast-api'
```

Then trigger manually or connect to GitHub:

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Monitoring

View logs in Cloud Console:

```bash
gcloud logs read --service package-forecast-api --limit 50
```

## Cost Estimation

Cloud Run pricing (as of 2024):
- **Compute**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second
- **Requests**: $0.40 per million requests
- **Free tier**: 2 million requests/month, 360,000 GiB-seconds

For a low-traffic forecasting API (~1000 requests/day), estimated cost: **~$5-10/month**.

## Alternative Cloud Providers

### AWS ECS Fargate

```bash
# Build and tag
docker build -t package-forecast-api .
docker tag package-forecast-api:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/package-forecast-api:latest

# Push to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/package-forecast-api:latest

# Create Fargate service (use AWS Console or CDK)
```

### Azure Container Instances

```bash
# Login
az login

# Create container
az container create \
  --resource-group myResourceGroup \
  --name package-forecast-api \
  --image youracr.azurecr.io/package-forecast-api \
  --dns-name-label package-forecast \
  --ports 8000
```

## Security Considerations

For production deployments:

1. **Authentication**: Use API keys or OAuth
2. **Rate Limiting**: Prevent abuse
3. **HTTPS Only**: Cloud Run provides this by default
4. **Secrets Management**: Use Cloud Secret Manager for sensitive configs
5. **Network Policies**: Restrict ingress to specific IPs if needed

## Automated Retraining

For continuous model updates, add a Cloud Scheduler job:

```bash
# Create a scheduled job to retrain weekly
gcloud scheduler jobs create http retrain-models \
  --schedule="0 2 * * 0" \
  --uri="https://package-forecast-api-xxxxx-uc.a.run.app/retrain" \
  --http-method=POST
```

(Note: Would need to implement `/retrain` endpoint)
