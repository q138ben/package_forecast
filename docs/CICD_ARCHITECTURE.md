# CI/CD Architecture Diagram

## Overall Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GITHUB REPOSITORY                                 │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐│
│  │  Source    │  │  Data Files  │  │   Tests     │  │  Workflows     ││
│  │   Code     │  │              │  │             │  │  (.github/)    ││
│  └────────────┘  └──────────────┘  └─────────────┘  └────────────────┘│
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               │ Push/PR
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GITHUB ACTIONS (CI/CD)                              │
│                                                                           │
│  ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐ │
│  │ Data Validation  │────▶│  Test & Lint     │────▶│ Model Training  │ │
│  │  - Schema check  │     │  - Unit tests    │     │ - Train Prophet │ │
│  │  - Quality check │     │  - Coverage      │     │ - CV evaluation │ │
│  │  - Profile data  │     │  - Ruff linting  │     │ - Extract       │ │
│  └──────────────────┘     └──────────────────┘     │   metrics       │ │
│                                                     └────────┬────────┘ │
│                                                              │          │
│                                                              ▼          │
│  ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐ │
│  │ Build Container  │────▶│  Deploy to       │────▶│ Post-Deploy     │ │
│  │  - Docker build  │     │  Cloud Run       │     │ - Tag release   │ │
│  │  - Push to GCR   │     │  - Smoke tests   │     │ - Cleanup old   │ │
│  │  - Tag image     │     │  - Verify        │     │   revisions     │ │
│  └──────────────────┘     └──────────────────┘     └─────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
                               │
                               │ Artifacts & Deployment
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD PLATFORM                               │
│                                                                           │
│  ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐ │
│  │ Cloud Storage    │     │  Container       │     │  Cloud Run      │ │
│  │  (Artifacts)     │     │  Registry        │     │  (Service)      │ │
│  │                  │     │                  │     │                 │ │
│  │ ├─ v1/           │     │ ├─ image:v1     │     │ ├─ Revision 1   │ │
│  │ ├─ v2/           │     │ ├─ image:v2     │     │ ├─ Revision 2   │ │
│  │ ├─ latest.txt    │     │ └─ image:latest │     │ └─ Revision 3   │ │
│  │ └─ prod.txt      │     │                  │     │   (active)      │ │
│  └──────────────────┘     └──────────────────┘     └─────────────────┘ │
│                                                                           │
│  ┌──────────────────┐     ┌──────────────────┐                          │
│  │ Cloud Monitoring │     │  Cloud Logging   │                          │
│  │  - Metrics       │     │  - Service logs  │                          │
│  │  - Alerts        │     │  - Error traces  │                          │
│  └──────────────────┘     └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               │ Monitoring
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MONITORING & ALERTING                                 │
│                                                                           │
│  ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐ │
│  │ Health Checks    │     │  Performance     │     │  Drift          │ │
│  │  Every 6 hours   │     │  Monitoring      │     │  Detection      │ │
│  │  - /health       │     │  - Latency       │     │  - Compare      │ │
│  │  - /ready        │     │  - CPU/Memory    │     │    training     │ │
│  │  - Endpoints     │     │  - Request count │     │    vs forecast  │ │
│  └──────────────────┘     └──────────────────┘     └─────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Alert on Failures                               │  │
│  │              (GitHub Issues / Email / Slack)                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Model Lifecycle

```
┌─────────────┐
│  Raw Data   │
└──────┬──────┘
       │
       │ Validation
       ▼
┌─────────────────┐
│ Validated Data  │
└──────┬──────────┘
       │
       │ Split
       ▼
┌──────────────────────────┐
│  Train Set │  Test Set   │
└──────┬─────┴─────────────┘
       │
       │ Training
       ▼
┌─────────────────┐
│ Trained Model   │
│  (Prophet)      │
└──────┬──────────┘
       │
       │ Evaluation
       ▼
┌─────────────────┐
│ Model Metrics   │
│  - RMSE         │
│  - MAE          │
│  - WAPE         │
└──────┬──────────┘
       │
       │ Threshold Check
       ▼
┌─────────────────┐      ┌─────────────┐
│  Pass?          │──No──▶│   Reject    │
└──────┬──────────┘      └─────────────┘
       │ Yes
       ▼
┌─────────────────┐
│  Register       │
│  Model          │
└──────┬──────────┘
       │
       │ Promote?
       ▼
┌─────────────────┐      ┌─────────────┐
│  Production?    │──No──▶│  Candidate  │
└──────┬──────────┘      └─────────────┘
       │ Yes
       ▼
┌─────────────────┐
│  Deploy to      │
│  Production     │
└──────┬──────────┘
       │
       │ Monitor
       ▼
┌─────────────────┐      ┌─────────────┐
│  Drift Check    │──Yes─▶│  Retrain    │
└──────┬──────────┘      └─────────────┘
       │ No
       │
       └──── Continue Serving ────┘
```

## Artifact Versioning Structure

```
GCS Bucket: gs://package-forecast-artifacts/
│
├── v20260227-143052-abc123d/
│   ├── location_A_forecast.csv
│   ├── location_A_results.json
│   ├── location_A_model.pkl
│   ├── location_A_train_data.csv
│   ├── location_A_test_data.csv
│   ├── location_B_forecast.csv
│   ├── location_B_results.json
│   ├── location_B_model.pkl
│   ├── location_B_train_data.csv
│   ├── location_B_test_data.csv
│   ├── location_C_forecast.csv
│   ├── location_C_results.json
│   ├── location_C_model.pkl
│   ├── location_C_train_data.csv
│   ├── location_C_test_data.csv
│   └── metrics-summary.json
│
├── v20260220-120000-xyz789d/
│   └── ... (same structure)
│
├── latest-version.txt          → "v20260227-143052-abc123d"
└── production-version.txt      → "v20260220-120000-xyz789d"
```

## Deployment Flow

```
┌────────────────┐
│  New Commit    │
│  to main       │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Data Valid?    │──No──▶ ⚠️  Warning (continue)
└───────┬────────┘
        │ Yes
        ▼
┌────────────────┐
│  Tests Pass?   │──No──▶ ❌ Stop
└───────┬────────┘
        │ Yes
        ▼
┌────────────────┐
│ Train Models   │
│ (if scheduled) │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Build          │
│ Container      │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Deploy to      │
│ Cloud Run      │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Smoke Tests?   │──No──▶ 🔄 Rollback
└───────┬────────┘
        │ Yes
        ▼
┌────────────────┐
│   ✅ Success   │
│  Tag Release   │
└────────────────┘
```

## Monitoring Loop

```
        ┌─────────────────┐
        │  Service        │
        │  Running        │
        └────────┬────────┘
                 │
         Every 6 hours
                 │
                 ▼
        ┌─────────────────┐
        │  Health Check   │
        └────────┬────────┘
                 │
          ┌──────┴──────┐
      Fail│             │Pass
          ▼             ▼
    ┌──────────┐  ┌─────────────┐
    │  Create  │  │   Check     │
    │  Alert   │  │   Drift     │
    │  Issue   │  └──────┬──────┘
    └──────────┘         │
                    ┌────┴────┐
                Drift│        │No Drift
                     ▼        ▼
              ┌──────────┐  ┌──────────┐
              │  Alert + │  │ Continue │
              │  Retrain │  │ Monitor  │
              └──────────┘  └──────────┘
```

## Components Interaction

```
┌────────────────────────────────────────────────────────────┐
│                    GitHub Actions                          │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Data    │  │  Model   │  │ Artifact │  │  Monitor │ │
│  │ Validate │  │ Training │  │   Mgmt   │  │          │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
└───────┼─────────────┼─────────────┼─────────────┼────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌───────────────────────────────────────────────────────────┐
│                   Google Cloud Platform                    │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │   GCS    │◀─│   GCR    │◀─│Cloud Run │◀─│   Mon    │ │
│  │Artifacts │  │ Images   │  │ Service  │  │ Metrics  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└────────────────────────────────────────────────────────────┘
        ▲             ▲             │             ▲
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                    Bidirectional sync
```

## File Organization

```
package_forecast/
│
├── .github/
│   └── workflows/
│       ├── ci-cd.yml              ← Main pipeline
│       ├── data-validation.yml    ← Data checks
│       ├── model-training.yml     ← Training jobs
│       ├── artifact-management.yml ← Version mgmt
│       └── monitoring.yml         ← Health checks
│
├── scripts/
│   ├── validate_data.py           ← Validation
│   ├── profile_data.py            ← Profiling
│   ├── extract_metrics.py         ← Metrics
│   ├── evaluate_models.py         ← Evaluation
│   ├── generate_evaluation_plots.py ← Plots
│   ├── check_thresholds.py        ← Thresholds
│   ├── register_model.py          ← Registry
│   ├── collect_performance_metrics.py ← Monitoring
│   ├── check_model_drift.py       ← Drift
│   ├── deploy.sh                  ← Deployment
│   └── rollback.sh                ← Rollback
│
├── config/
│   ├── model-thresholds.yml       ← Thresholds
│   └── deployment.yml             ← Env config
│
├── src/
│   └── models/
│       └── artifact_manager.py    ← Versioning
│
├── .model-registry/               ← Model records
│   ├── README.md
│   ├── v20260227-143052-abc.json
│   └── production.txt
│
└── docs/
    ├── CICD_GUIDE.md              ← Full guide
    └── CICD_QUICK_REFERENCE.md    ← Quick ref
```
