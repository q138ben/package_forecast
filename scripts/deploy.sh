#!/bin/bash
# Deployment script with environment support

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Loaded environment variables from .env"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
ENVIRONMENT=${1:-${ENVIRONMENT:-production}}
PROJECT_ID=${2:-${GCP_PROJECT_ID}}

if [ -z "$PROJECT_ID" ]; then
    log_error "GCP_PROJECT_ID not set. Usage: $0 <environment> <project_id>"
    exit 1
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Project ID: $PROJECT_ID"

# Set environment-specific variables
if [ "$ENVIRONMENT" = "production" ]; then
    SERVICE_NAME="${CLOUD_RUN_SERVICE_NAME:-package-forecast}"
    MEMORY="${CLOUD_RUN_MEMORY:-2Gi}"
    CPU="${CLOUD_RUN_CPU:-2}"
    MAX_INSTANCES="${CLOUD_RUN_MAX_INSTANCES:-10}"
    MIN_INSTANCES="${CLOUD_RUN_MIN_INSTANCES:-1}"
elif [ "$ENVIRONMENT" = "staging" ]; then
    SERVICE_NAME="${CLOUD_RUN_SERVICE_NAME:-package-forecast}-staging"
    MEMORY="${CLOUD_RUN_MEMORY:-1Gi}"
    CPU="${CLOUD_RUN_CPU:-1}"
    MAX_INSTANCES="${CLOUD_RUN_MAX_INSTANCES:-5}"
    MIN_INSTANCES="${CLOUD_RUN_MIN_INSTANCES:-0}"
else
    log_error "Invalid environment: $ENVIRONMENT. Use 'production' or 'staging'"
    exit 1
fi

REGION="${GCP_REGION:-us-central1}"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Please install it first."
    exit 1
fi

# Check authentication
log_info "Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated with GCP. Run 'gcloud auth login' first."
    exit 1
fi

# Set project
log_info "Setting GCP project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
log_info "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Build container
log_info "Building container image..."
gcloud builds submit --tag $IMAGE_TAG

# Deploy to Cloud Run
log_info "Deploying to Cloud Run ($ENVIRONMENT)..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_TAG \
    --platform managed \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout 300 \
    --max-instances $MAX_INSTANCES \
    --min-instances $MIN_INSTANCES \
    --allow-unauthenticated \
    --set-env-vars ENV=$ENVIRONMENT

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)')

log_info "Service deployed successfully!"
log_info "Service URL: $SERVICE_URL"

# Run smoke tests
log_info "Running smoke tests..."
sleep 10

# Test health endpoint
if curl -f -s "${SERVICE_URL}/health" > /dev/null; then
    log_info "✓ Health check passed"
else
    log_error "✗ Health check failed"
    exit 1
fi

# Test ready endpoint
if curl -f -s "${SERVICE_URL}/ready" > /dev/null; then
    log_info "✓ Ready check passed"
else
    log_error "✗ Ready check failed"
    exit 1
fi

# Test forecast endpoints
for location in A B C; do
    if curl -f -s "${SERVICE_URL}/?location=${location}" > /dev/null; then
        log_info "✓ Forecast endpoint for location $location passed"
    else
        log_error "✗ Forecast endpoint for location $location failed"
        exit 1
    fi
done

log_info "All smoke tests passed!"
log_info "Deployment to $ENVIRONMENT completed successfully"

# Print summary
echo ""
echo "========================================"
echo "Deployment Summary"
echo "========================================"
echo "Environment: $ENVIRONMENT"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "URL: $SERVICE_URL"
echo "========================================"
