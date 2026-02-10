# Deployment Guide

This project is configured for deployment to **Google Cloud Platform (GCP)** using Cloud Run. Cloud Run is a serverless platform that automatically scales your containerized application.

## Prerequisites

1.  **Google Cloud SDK**: Install the `gcloud` CLI tools.
2.  **GCP Project**: You need an active Google Cloud project with billing enabled.

## Configuration Files

*   **`Dockerfile`**: Defines the Python environment and installation steps. It uses a lightweight `python:3.11-slim` image.
*   **`.dockerignore`**: Ensures unneeded files (like notebooks, git history) are not uploaded to the build context.
*   **`scripts/deploy_gcp.sh`**: Helper script to automate the build and deploy process.

## How to Deploy

1.  **Login to Google Cloud**:
    ```bash
    gcloud auth login
    ```

2.  **Run the Deployment Script**:
    Replace `YOUR_PROJECT_ID` with your actual GCP project ID.
    ```bash
    ./scripts/deploy_gcp.sh YOUR_PROJECT_ID
    ```

    You can optionally specify a region (default is `us-central1`):
    ```bash
    ./scripts/deploy_gcp.sh YOUR_PROJECT_ID europe-west1
    ```

## What Happens During Deployment?

The script uses `gcloud run deploy --source .` which simplifies the process:
1.  **Uploads** your source code (respecting `.dockerignore`).
2.  **Builds** a container using the `Dockerfile` via Google Cloud Build.
3.  **Deploys** the container to Cloud Run (Managed) as a public service.

## Testing the Cloud API

Once deployed, you will get a URL like `https://package-forecast-xyz-uc.a.run.app`.

Test it using curl:
```bash
curl https://package-forecast-xyz-uc.a.run.app/forecast/A
```
