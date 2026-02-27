# CI/CD Setup Checklist

Use this checklist to ensure your CI/CD pipeline is properly configured and ready to use.

## ☐ Prerequisites

### GitHub Repository
- [ ] Repository created and code pushed
- [ ] Main branch protection enabled (recommended)
- [ ] GitHub Actions enabled

### Local Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Update `GCP_PROJECT_ID` in `.env` with your project ID
- [ ] Update other variables in `.env` as needed
- [ ] Verify `.env` is in `.gitignore` (already configured)

### Google Cloud Platform
- [ ] GCP Project created
- [ ] Billing enabled
- [ ] gcloud CLI installed locally

### Local Environment
- [ ] Python 3.11+ installed
- [ ] Git configured
- [ ] GitHub CLI installed (optional but recommended)

## ☐ Google Cloud Setup

### 1. Enable Required APIs
```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  storage.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

- [ ] Cloud Build API enabled
- [ ] Cloud Run API enabled
- [ ] Container Registry API enabled
- [ ] Cloud Storage API enabled
- [ ] Cloud Monitoring API enabled
- [ ] Cloud Logging API enabled

### 2. Create Service Account
```bash
# Create service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" \
  --project=YOUR_PROJECT_ID

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

- [ ] Service account created
- [ ] Cloud Run Admin role granted
- [ ] Cloud Build Editor role granted
- [ ] Storage Admin role granted
- [ ] Service Account User role granted
- [ ] Monitoring Viewer role granted
- [ ] Service account key downloaded

### 3. Create GCS Bucket
```bash
# load env variables
export $(grep -v '^#' .env | xargs)

# Create bucket for artifacts
gsutil mb -p $GCP_PROJECT_ID -l us-central1 gs://package-forecast-artifacts
# Optional: Create staging bucket
gsutil mb -p $GCP_PROJECT_ID -l $GCP_REGION gs://package-forecast-artifacts-staging

# Set lifecycle policy (optional)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["v"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://package-forecast-artifacts
```

- [ ] Production artifacts bucket created
- [ ] Staging artifacts bucket created (optional)
- [ ] Lifecycle policy configured (optional)

## ☐ GitHub Secrets Configuration

### Add Secrets to Repository
Go to: Repository → Settings → Secrets and variables → Actions → New repository secret

```bash
# Using GitHub CLI
gh secret set GCP_PROJECT_ID --body "YOUR_PROJECT_ID"
gh secret set GCP_SA_KEY < key.json
```

- [ ] `GCP_PROJECT_ID` secret added
- [ ] `GCP_SA_KEY` secret added (service account JSON key)

### Verify Secrets
```bash
gh secret list
```

- [ ] Secrets are visible in the list

## ☐ Local Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

- [ ] All dependencies installed successfully

### 2. Test Data Validation
```bash
python scripts/validate_data.py --input data-4-.csv --output validation-report.json
```

- [ ] Data validation runs successfully
- [ ] validation-report.json created

### 3. Test Model Training
```bash
python main.py train --data-path data-4-.csv --artifacts-dir artifacts
```

- [ ] Training completes successfully
- [ ] Artifacts created in artifacts/ directory
- [ ] All location models trained

### 4. Test Forecasting
```bash
python main.py forecast --artifacts-dir artifacts
```

- [ ] Forecasts generated successfully
- [ ] Forecast CSVs created

### 5. Test API Locally
```bash
# Terminal 1: Start API
python main.py serve --artifacts-dir artifacts

# Terminal 2: Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/forecast/A
```

- [ ] API starts successfully
- [ ] Health endpoint works
- [ ] Ready endpoint works
- [ ] Forecast endpoints work

### 6. Test Docker Build
```bash
docker build -t package-forecast-test .
docker run -p 8000:8080 package-forecast-test
curl http://localhost:8000/health
```

- [ ] Docker image builds successfully
- [ ] Container runs successfully
- [ ] Endpoints accessible in container

## ☐ Initial Deployment

### 1. Manual Deployment Test
```bash
# Make sure .env is configured first!
# Set your project ID in .env file

./scripts/deploy.sh staging
```

- [ ] `.env` file created and configured
- [ ] Deployment script runs successfully
- [ ] Service deployed to Cloud Run
- [ ] Smoke tests pass
- [ ] Service URL obtained

### 2. Test Deployed Service
```bash
SERVICE_URL=$(gcloud run services describe package-forecast-staging \
  --region us-central1 \
  --format 'value(status.url)')

curl $SERVICE_URL/health
curl $SERVICE_URL/ready
curl $SERVICE_URL/?location=A
```

- [ ] Health check passes
- [ ] Ready check passes
- [ ] Forecast endpoints work

## ☐ CI/CD Pipeline Testing

### 1. Test Data Validation Workflow
```bash
gh workflow run data-validation.yml
gh run watch
```

- [ ] Workflow triggers successfully
- [ ] Data validation passes
- [ ] Artifacts uploaded

### 2. Test Model Training Workflow
```bash
gh workflow run model-training.yml
gh run watch
```

- [ ] Workflow triggers successfully
- [ ] Models train successfully
- [ ] Artifacts uploaded to GCS
- [ ] Model registered

### 3. Test Main CI/CD Pipeline
```bash
# Make a small change and push
git add .
git commit -m "test: trigger CI/CD pipeline"
git push origin main

gh run watch
```

- [ ] All jobs run successfully
- [ ] Tests pass
- [ ] Models train (if applicable)
- [ ] Container builds
- [ ] Service deploys
- [ ] Smoke tests pass

### 4. Test Artifact Management
```bash
# List versions
gh workflow run artifact-management.yml -f action=list-versions

# Wait for it to complete, then check output
gh run view --log
```

- [ ] Workflow runs successfully
- [ ] Versions listed correctly

### 5. Test Monitoring
```bash
gh workflow run monitoring.yml
gh run watch
```

- [ ] Health checks run
- [ ] Performance metrics collected
- [ ] No alerts triggered (if service is healthy)

## ☐ Configuration Review

### 1. Review Thresholds
Edit `config/model-thresholds.yml` and adjust if needed:

- [ ] Overall score threshold appropriate
- [ ] WAPE threshold appropriate
- [ ] RMSE threshold appropriate
- [ ] MAE threshold appropriate

### 2. Review Deployment Config
Edit `config/deployment.yml` and verify:

- [ ] GCP project ID correct
- [ ] Region correct
- [ ] Resource limits appropriate
- [ ] Monitoring settings appropriate

### 3. Review Schedule
Check workflow schedules in:
- [ ] `data-validation.yml` - Daily at 2 AM UTC
- [ ] `model-training.yml` - Weekly on Sundays at 3 AM UTC
- [ ] `monitoring.yml` - Every 6 hours

Adjust if needed for your timezone and requirements.

## ☐ Monitoring Setup

### 1. Verify Health Checks
- [ ] Health check workflow runs every 6 hours
- [ ] Alerts create GitHub issues on failure
- [ ] Issue labels configured correctly

### 2. Set Up Additional Alerting (Optional)
- [ ] Configure email notifications
- [ ] Configure Slack notifications
- [ ] Configure PagerDuty integration

### 3. Set Up Dashboard (Optional)
- [ ] Create Cloud Monitoring dashboard
- [ ] Add key metrics (latency, errors, requests)
- [ ] Share dashboard with team

## ☐ Documentation

### 1. Update README
- [ ] Add CI/CD pipeline overview
- [ ] Add deployment instructions
- [ ] Add troubleshooting section

### 2. Team Onboarding
- [ ] Share CICD_GUIDE.md with team
- [ ] Share CICD_QUICK_REFERENCE.md
- [ ] Conduct walkthrough session

### 3. Create Runbooks
- [ ] Deployment runbook
- [ ] Rollback runbook
- [ ] Incident response runbook

## ☐ Production Readiness

### 1. Branch Protection
Enable on main branch:
- [ ] Require pull request reviews
- [ ] Require status checks to pass
- [ ] Require branches to be up to date
- [ ] Include administrators

### 2. Access Control
- [ ] Limit who can approve deployments
- [ ] Set up GitHub environments (optional)
- [ ] Configure required reviewers

### 3. Backup & Recovery
- [ ] Verify artifact retention policy
- [ ] Test rollback procedure
- [ ] Document recovery procedures

### 4. Cost Monitoring
- [ ] Set up billing alerts
- [ ] Review Cloud Run pricing
- [ ] Review Cloud Storage pricing
- [ ] Review Cloud Build pricing

## ☐ Go-Live Checklist

### Pre-Launch
- [ ] All checklist items above completed
- [ ] Staging environment tested
- [ ] Production deployment tested
- [ ] Rollback tested
- [ ] Team trained

### Launch
- [ ] Deploy to production
- [ ] Verify all endpoints
- [ ] Monitor for 24 hours
- [ ] Review logs and metrics

### Post-Launch
- [ ] Document any issues encountered
- [ ] Update procedures if needed
- [ ] Schedule regular reviews
- [ ] Set up weekly status reports

## ☐ Ongoing Maintenance

### Weekly
- [ ] Review monitoring alerts
- [ ] Check model performance
- [ ] Review drift reports
- [ ] Check resource utilization

### Monthly
- [ ] Review and cleanup old artifacts
- [ ] Update dependencies
- [ ] Review and update thresholds
- [ ] Review cost reports

### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Update documentation
- [ ] Team retrospective

## 🎉 Completion

Once all items are checked:
- [ ] Pipeline is production-ready
- [ ] Team is trained
- [ ] Documentation is complete
- [ ] Monitoring is active

---

**Need Help?**
- See `docs/CICD_GUIDE.md` for detailed documentation
- See `docs/CICD_QUICK_REFERENCE.md` for commands
- Check GitHub Actions logs for troubleshooting
- Review Cloud Run logs in GCP Console
