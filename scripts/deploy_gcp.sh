#!/bin/bash

# Deployment script for Google Cloud Run
# Usage: ./scripts/deploy_gcp.sh [PROJECT_ID] [REGION]

# Default values
PROJECT_ID=$1
REGION=${2:-"us-central1"}
APP_NAME="package-forecast"

# Check if project ID is provided
if [ -z "$PROJECT_ID" ]; then
    echo "Error: Google Cloud Project ID is required."
    echo "Usage: ./scripts/deploy_gcp.sh <PROJECT_ID> [REGION]"
    exit 1
fi

echo "========================================================"
echo "Deploying $APP_NAME to Google Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "========================================================"

# Enable necessary services
echo "Enabling necessary APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com --project $PROJECT_ID

# Deploy from source (handles build and deploy in one step)
echo "Step 1: Building and Deploying to Cloud Run..."
# This command automatically uses the Dockerfile in the current directory
gcloud run deploy $APP_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --project $PROJECT_ID

if [ $? -eq 0 ]; then
    echo "========================================================"
    echo "Deployment Success! Your API is live."
    echo "========================================================"
else
    echo "Deployment failed."
    exit 1
fi
