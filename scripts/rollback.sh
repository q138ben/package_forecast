#!/bin/bash
# Rollback deployment to a previous version

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
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
ENVIRONMENT=${1:-${ENVIRONMENT:-production}}
PROJECT_ID=${2:-${GCP_PROJECT_ID}}

if [ -z "$PROJECT_ID" ]; then
    log_error "GCP${CLOUD_RUN_SERVICE_NAME:-package-forecast}"
elif [ "$ENVIRONMENT" = "staging" ]; then
    SERVICE_NAME="${CLOUD_RUN_SERVICE_NAME:-package-forecast}-staging"
else
    log_error "Invalid environment: $ENVIRONMENT"
    exit 1
fi

REGION="${GCP_REGION:-us-central1}ackage-forecast-staging"
else
    log_error "Invalid environment: $ENVIRONMENT"
    exit 1
fi

REGION="us-central1"

log_info "Rolling back $SERVICE_NAME in $ENVIRONMENT..."

# Get list of revisions
log_info "Fetching available revisions..."
gcloud run revisions list \
    --service $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --format="table(name,metadata.creationTimestamp,status.conditions[0].status)"

# Get the previous revision (second in the list)
PREVIOUS_REVISION=$(gcloud run revisions list \
    --service $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --format="value(name)" \
    --sort-by="~metadata.creationTimestamp" \
    --limit=2 | tail -n 1)

if [ -z "$PREVIOUS_REVISION" ]; then
    log_error "No previous revision found to rollback to"
    exit 1
fi

log_info "Rolling back to revision: $PREVIOUS_REVISION"

# Perform rollback
gcloud run services update-traffic $SERVICE_NAME \
    --to-revisions=$PREVIOUS_REVISION=100 \
    --region $REGION \
    --project $PROJECT_ID

log_info "Rollback completed successfully"

# Verify
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --format 'value(status.url)')

log_info "Verifying rolled back service..."
sleep 10

if curl -f -s "${SERVICE_URL}/health" > /dev/null; then
    log_info "✓ Service is healthy after rollback"
else
    log_error "✗ Service health check failed after rollback"
    exit 1
fi

log_info "Rollback verification complete"
