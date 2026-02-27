# Environment Configuration Guide

## Overview

This project uses environment variables for configuration, stored in a `.env` file that is excluded from version control.

## Setup

### 1. Copy the Example File
```bash
cp .env.example .env
```

### 2. Edit Configuration
Open `.env` and update the values for your environment:

```bash
# Required: Your Google Cloud Project ID
GCP_PROJECT_ID=your-actual-project-id

# Optional: Update other values as needed
GCP_REGION=us-central1
CLOUD_RUN_SERVICE_NAME=package-forecast
```

### 3. Verify Configuration
```bash
# Test that environment loads correctly
python -c "from src.config import get_project_config; print(get_project_config())"
```

## Environment Variables Reference

### Google Cloud Platform

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | **Required** | Your GCP project ID |
| `GCP_REGION` | `us-central1` | GCP region for deployment |
| `GCP_SERVICE_ACCOUNT_EMAIL` | - | Service account email |

### Cloud Run

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUD_RUN_SERVICE_NAME` | `package-forecast` | Cloud Run service name |
| `CLOUD_RUN_MEMORY` | `2Gi` | Memory allocation |
| `CLOUD_RUN_CPU` | `2` | CPU allocation |
| `CLOUD_RUN_MAX_INSTANCES` | `10` | Maximum instances |
| `CLOUD_RUN_MIN_INSTANCES` | `1` | Minimum instances |

### Artifact Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTIFACTS_BUCKET` | `gs://package-forecast-artifacts` | GCS bucket for models |
| `ARTIFACTS_DIR` | `artifacts` | Local artifacts directory |

### Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_VERSION` | `auto` | Model version (auto-generated if 'auto') |
| `CV_FOLDS` | `5` | Cross-validation folds |
| `TEST_DAYS` | `30` | Days for test set |
| `HORIZON_DAYS` | `30` | Forecast horizon |

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8080` | API server port |
| `LOG_LEVEL` | `INFO` | Logging level |

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment name (development/staging/production) |
| `PYTHON_VERSION` | `3.11` | Python version |

## Usage in Code

### Python Scripts

```python
from src.config import get_env, get_project_config

# Get single variable
project_id = get_env('GCP_PROJECT_ID')

# Get project configuration
config = get_project_config()
print(config['project_id'])
print(config['region'])
print(config['service_name'])
print(config['artifacts_bucket'])

# Get with default
api_host = get_env('API_HOST', '0.0.0.0')
```

### Bash Scripts

```bash
# Load .env file (already done in deploy.sh and rollback.sh)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use variables
echo "Project: $GCP_PROJECT_ID"
echo "Region: $GCP_REGION"
```

### Main Application

The `.env` file is automatically loaded when importing from `src.config`:

```python
# main.py
from src.config import load_env_file, get_env

# Explicitly load (already done in main.py)
load_env_file()

# Use anywhere in the application
host = get_env('API_HOST', '0.0.0.0')
```

## Environment-Specific Configuration

### Development
```bash
ENVIRONMENT=development
GCP_PROJECT_ID=dev-project-123
CLOUD_RUN_SERVICE_NAME=package-forecast-dev
LOG_LEVEL=DEBUG
```

### Staging
```bash
ENVIRONMENT=staging
GCP_PROJECT_ID=staging-project-456
CLOUD_RUN_SERVICE_NAME=package-forecast-staging
LOG_LEVEL=INFO
CLOUD_RUN_MIN_INSTANCES=0
CLOUD_RUN_MAX_INSTANCES=5
```

### Production
```bash
ENVIRONMENT=production
GCP_PROJECT_ID=prod-project-789
CLOUD_RUN_SERVICE_NAME=package-forecast
LOG_LEVEL=WARNING
CLOUD_RUN_MIN_INSTANCES=1
CLOUD_RUN_MAX_INSTANCES=10
```

## Deployment Scripts

The deployment scripts automatically load environment variables:

### Deploy
```bash
# Uses .env file automatically
./scripts/deploy.sh

# Or override environment
./scripts/deploy.sh staging

# Or override project ID
./scripts/deploy.sh production my-other-project-id
```

### Rollback
```bash
# Uses .env file automatically
./scripts/rollback.sh

# Or override
./scripts/rollback.sh staging my-project-id
```

## GitHub Actions

For CI/CD, secrets are stored in GitHub repository secrets (not in .env):

1. Go to Repository → Settings → Secrets and variables → Actions
2. Add secrets:
   - `GCP_PROJECT_ID`
   - `GCP_SA_KEY`

Workflows reference these as `${{ secrets.GCP_PROJECT_ID }}`.

## Security Best Practices

### ✅ DO

- Keep `.env` in `.gitignore` (already configured)
- Use `.env.example` as a template (already created)
- Rotate sensitive values regularly
- Use different values for each environment
- Document all variables in this README

### ❌ DON'T

- Commit `.env` to git
- Share `.env` files directly
- Use production credentials in development
- Include API keys or secrets in `.env.example`

## Troubleshooting

### Environment Not Loading

**Problem:** Variables from `.env` not being used

**Solution:**
```python
# Explicitly load
from src.config import load_env_file
load_env_file()

# Or check if file exists
import os
from pathlib import Path
env_file = Path('.env')
print(f".env exists: {env_file.exists()}")
```

### Missing Required Variables

**Problem:** `GCP_PROJECT_ID` not set

**Solution:**
1. Check `.env` file exists: `ls -la .env`
2. Verify it's populated: `cat .env`
3. Check for typos in variable names
4. Ensure no spaces around `=`: `KEY=value` not `KEY = value`

### Scripts Can't Find Variables

**Problem:** Bash scripts don't see environment variables

**Solution:**
```bash
# Make sure .env is being loaded
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Loaded .env"
else
    echo "Error: .env not found"
    exit 1
fi
```

### Python Module Import Errors

**Problem:** `ImportError: cannot import name 'get_env' from 'src.config'`

**Solution:**
```python
# Add project root to Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_env
```

## Migration from Hardcoded Values

If you're migrating from hardcoded values:

1. **Find hardcoded values:**
   ```bash
   grep -r "us-central1" --include="*.py" --include="*.sh"
   grep -r "package-forecast" --include="*.py" --include="*.sh"
   ```

2. **Replace with environment variables:**
   ```python
   # Before
   region = "us-central1"
   
   # After
   from src.config import get_env
   region = get_env('GCP_REGION', 'us-central1')
   ```

3. **Update .env.example** with new variables

4. **Test thoroughly** in development before deploying

## Additional Resources

- [Python-dotenv documentation](https://pypi.org/project/python-dotenv/) (alternative library if needed)
- [12-Factor App Config](https://12factor.net/config) - Best practices
- [Google Cloud SDK Configuration](https://cloud.google.com/sdk/gcloud/reference/config)

## Support

For issues with environment configuration:
1. Verify `.env` file exists and is readable
2. Check for syntax errors (no spaces, proper quoting)
3. Ensure variables are exported in bash scripts
4. Check Python path includes project root
5. Review logs for specific error messages
