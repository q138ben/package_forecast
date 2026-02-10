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
gcloud services enable cloudbuild.googleapis.com run.googleapis.com --project $PROJECT_ID

# Build the Docker image
echo "Step 1: Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$APP_NAME --project $PROJECT_ID

if [ $? -ne 0 ]; then
    echo "Build failed! Exiting."
    exit 1
fi

# Deploy to Cloud Run
echo "Step 2: Deploying to Cloud Run..."
gcloud run deploy $APP_NAME \
  --image gcr.io/$PROJECT_ID/$APP_NAME \
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
