# CI/CD Pipeline Documentation

## Overview

This comprehensive CI/CD pipeline automates the entire machine learning lifecycle from data validation to model deployment with versioning, monitoring, and rollback capabilities.

## Pipeline Components

### 1. Data Validation (`data-validation.yml`)

**Triggers:**
- Daily at 2 AM UTC (scheduled)
- Manual dispatch
- Changes to data files or processing code

**Features:**
- Schema validation
- Data quality checks
- Temporal consistency verification
- Statistical property validation
- Automated reporting with HTML profiles

**Outputs:**
- `validation-report.json` - Validation results
- `data-profile.html` - Data profiling report

### 2. Model Training & Evaluation (`model-training.yml`)

**Triggers:**
- Weekly on Sundays at 3 AM UTC (scheduled)
- Manual dispatch with options
- Changes to model or data code

**Features:**
- Automated versioning with timestamps and git commits
- Training all location models with cross-validation
- Comprehensive model evaluation
- Artifact management with GCS upload
- Model registry updates
- Performance threshold checks

**Outputs:**
- Trained model artifacts
- Training metrics summary
- Evaluation reports
- Visualization plots

**Model Versioning:**
Format: `v{YYYYMMDD-HHmmss}-{git_short_sha}`
Example: `v20260227-143052-a1b2c3d`

### 3. Main CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to main/develop branches
- Pull requests to main
- Manual dispatch with deployment options

**Jobs:**

#### 3.1 Validate Data
- Runs data validation on main branch pushes
- Uploads validation reports
- Warns on validation failures

#### 3.2 Test & Lint
- Runs all unit tests with coverage
- Performs code linting with ruff
- Uploads coverage reports to Codecov

#### 3.3 Train Models
- Generates unique model version
- Trains Prophet models for all locations
- Generates forecasts
- Evaluates performance
- Uploads artifacts to GCS
- Registers model in registry

#### 3.4 Build & Push
- Builds Docker container with multi-stage caching
- Pushes to Google Container Registry
- Tags with timestamp and git SHA

#### 3.5 Deploy
- Deploys to Cloud Run with environment-specific configuration
- Injects model version as environment variable
- Waits for service to be ready
- Verifies all endpoints
- Creates deployment record

#### 3.6 Post-Deployment
- Tags successful deployments in git
- Cleans up old Cloud Run revisions (keeps last 5)

### 4. Artifact Management (`artifact-management.yml`)

**Actions:**
- `list-versions` - List all model versions in GCS
- `promote-to-production` - Promote a version to production
- `rollback` - Rollback to a previous version
- `cleanup-old` - Remove old model versions (keeps last 10)

**Usage:**
```bash
# Promote a model to production
gh workflow run artifact-management.yml \
  -f action=promote-to-production \
  -f version=v20260227-143052-a1b2c3d
```

### 5. Monitoring & Alerts (`monitoring.yml`)

**Schedule:** Every 6 hours

**Monitors:**
- Service health endpoints
- API endpoint availability
- Performance metrics (latency, CPU, memory)
- Model drift detection
- Cost estimation

**Alerts:**
- Creates GitHub issues on failures
- Includes detailed diagnostic information
- Labels issues for triage

## Versioning Strategy

### Model Versions
- **Format:** `v{YYYYMMDD-HHmmss}-{git_short_sha}`
- **Storage:** GCS bucket with version folders
- **Registry:** `.model-registry/` directory in repo

### Artifact Versions
- Each model version has its own folder in GCS
- Contains all artifacts (models, forecasts, metrics, data splits)
- `latest-version.txt` points to most recent version
- `production-version.txt` points to production version

## Deployment Environments

### Production
- Service: `package-forecast`
- Resources: 2 vCPU, 2Gi RAM
- Scaling: 1-10 instances
- Region: us-central1

### Staging
- Service: `package-forecast-staging`
- Resources: 1 vCPU, 1Gi RAM
- Scaling: 0-5 instances
- Region: us-central1

## Monitoring & Reliability

### Health Checks
- `/health` - Basic service health
- `/ready` - Readiness with artifact check
- Automated every 6 hours
- Creates alerts on failure

### Performance Monitoring
- Request count and latency
- CPU and memory utilization
- Collected from Cloud Monitoring
- Stored as artifacts

### Model Drift Detection
- Compares forecast statistics to training data
- Thresholds: 30% mean deviation, 50% std deviation
- Automated detection every monitoring cycle
- Reports severity levels

### Quality Thresholds
Defined in `config/model-thresholds.yml`:
- Overall score: minimum 70/100
- WAPE: maximum 20%
- RMSE: maximum 150 packages
- MAE: maximum 100 packages
- Interval coverage: minimum 80%

## Rollback Procedures

### Automated Rollback
If deployment verification fails, previous revision is automatically active

### Manual Rollback
Using GitHub Actions:
```bash
gh workflow run artifact-management.yml \
  -f action=rollback \
  -f version=v20260227-120000-abc123d
```

Using script:
```bash
./scripts/rollback.sh production $GCP_PROJECT_ID
```

### Cloud Run Console
1. Go to Cloud Run service
2. View "Revisions" tab
3. Select previous revision
4. Click "Manage Traffic"
5. Route 100% to previous revision

## Best Practices

### 1. Model Training
- Train weekly or when significant data changes occur
- Review metrics before promoting to production
- Maintain at least 180 days of training data

### 2. Artifact Management
- Keep production models for 1 year
- Archive or delete old non-production versions after 90 days
- Tag important versions in git

### 3. Deployment
- Always deploy to staging first (manual)
- Run smoke tests after deployment
- Monitor for 24 hours before considering stable

### 4. Monitoring
- Review health check results daily
- Investigate drift reports weekly
- Set up additional alerting channels (Slack, PagerDuty)

## Secrets Configuration

Required GitHub Secrets:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GCP_SA_KEY` - Service account JSON key with permissions:
  - Cloud Run Admin
  - Cloud Build Editor
  - Storage Admin
  - Service Usage Consumer
  - Monitoring Viewer

## Local Development

### Train Models Locally
```bash
python main.py train --data-path data-4-.csv --artifacts-dir artifacts
```

### Generate Forecasts
```bash
python main.py forecast --artifacts-dir artifacts
```

### Run Validation
```bash
python scripts/validate_data.py --input data-4-.csv
```

### Test Deployment
```bash
./scripts/deploy.sh staging $GCP_PROJECT_ID
```

## Troubleshooting

### Pipeline Failures

#### Data Validation Fails
1. Check validation report artifact
2. Review data quality issues
3. Fix data or adjust validation rules
4. Re-run validation

#### Model Training Fails
1. Check training logs
2. Verify data quality
3. Review Prophet parameters
4. Check for memory issues

#### Deployment Fails
1. Check Cloud Run logs
2. Verify container builds successfully
3. Test endpoints manually
4. Check IAM permissions

#### Health Checks Fail
1. Check service logs in Cloud Run
2. Verify artifacts exist in GCS
3. Test endpoints directly
4. Check resource limits

### Common Issues

**Issue:** Container build timeout
**Solution:** Increase timeout in Cloud Build configuration

**Issue:** Model artifacts not found
**Solution:** Verify GCS bucket permissions and artifact upload succeeded

**Issue:** High memory usage
**Solution:** Increase Cloud Run memory allocation or optimize model size

**Issue:** Slow response times
**Solution:** Increase CPU allocation or enable request caching

## Metrics & KPIs

Track these metrics for pipeline health:
- Pipeline success rate (target: >95%)
- Deployment frequency (current: weekly)
- Mean time to recovery (target: <1 hour)
- Model accuracy (WAPE target: <15%)
- API latency (target: <500ms p95)
- Service uptime (target: >99.5%)

## Future Enhancements

Potential improvements:
1. A/B testing framework for model versions
2. Automated performance comparison reports
3. Multi-region deployment
4. Canary deployment strategy
5. Advanced drift detection with statistical tests
6. Integration with ML monitoring platforms (Evidently AI, WhyLabs)
7. Cost optimization recommendations
8. Automated retraining triggers based on drift

## Support

For issues or questions:
1. Check workflow run logs in GitHub Actions
2. Review Cloud Run logs in GCP Console
3. Check monitoring artifacts
4. Create an issue in the repository

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Prophet Documentation](https://facebook.github.io/prophet/)
- [Model Deployment Best Practices](https://ml-ops.org/)
