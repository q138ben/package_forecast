# Vertex AI Pipeline Architecture Guide

This document outlines the recommended architecture for migrating the package forecast project to **Google Cloud Vertex AI Pipelines**. Use this as a reference when restructuring the project for production ML pipelines.

---

## Table of Contents

1. [Overview](#overview)
2. [Recommended Project Structure](#recommended-project-structure)
3. [Pipeline Components](#pipeline-components)
4. [Component Mapping](#component-mapping)
5. [Example Pipeline Definition](#example-pipeline-definition)
6. [Key Principles](#key-principles)
7. [Migration Steps](#migration-steps)

---

## Overview

Vertex AI Pipelines uses **Kubeflow Pipelines (KFP) v2** to orchestrate ML workflows. The key idea is to break down the training process into discrete, containerizable **components** that pass data via **artifacts** stored in Google Cloud Storage (GCS).

### Benefits
- **Reproducibility**: Each run is versioned and trackable
- **Scalability**: Components run on managed infrastructure
- **Modularity**: Components can be reused across pipelines
- **Observability**: Built-in logging, metrics, and lineage tracking

---

## Recommended Project Structure

```
package_forecast/
├── components/                    # Pipeline components (each is containerizable)
│   ├── data_ingestion/
│   │   ├── component.yaml         # Component spec
│   │   ├── Dockerfile
│   │   └── src/
│   │       └── ingest.py
│   ├── data_validation/
│   │   ├── component.yaml
│   │   └── src/
│   │       └── validate.py
│   ├── preprocessing/
│   │   ├── component.yaml
│   │   └── src/
│   │       └── preprocess.py
│   ├── training/
│   │   ├── component.yaml
│   │   └── src/
│   │       └── train.py
│   ├── evaluation/
│   │   ├── component.yaml
│   │   └── src/
│   │       └── evaluate.py
│   └── deployment/
│       ├── component.yaml
│       └── src/
│           └── deploy.py
├── pipelines/                     # Pipeline definitions
│   ├── training_pipeline.py       # KFP pipeline definition
│   └── inference_pipeline.py
├── src/                           # Shared library code
│   ├── models/
│   ├── data/
│   ├── visualization/
│   └── utils/
├── configs/                       # Pipeline & model configs
│   ├── pipeline_config.yaml
│   └── model_config.yaml
├── tests/
├── Dockerfile                     # Base image for components
├── requirements.txt
└── setup.py                       # Package your src/ as installable
```

---

## Pipeline Components

### Pipeline Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Ingest    │ -> │  Validate   │ -> │  Preprocess │ -> │   Train     │ -> │  Evaluate   │
│   Data      │    │   Data      │    │   & Split   │    │   Model     │    │   Model     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                                    │
                                                                                    v
                                                                           ┌─────────────┐
                                                                           │   Deploy    │
                                                                           │  (if pass)  │
                                                                           └─────────────┘
```

### Component Descriptions

| Component | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| **Data Ingestion** | Load raw data from source (GCS, BigQuery, etc.) | Data source URI | Raw dataset artifact |
| **Data Validation** | Validate data quality, schema, statistics | Raw dataset | Validated dataset, validation report |
| **Preprocessing** | Clean data, prepare features, train/test split | Validated dataset, location, test_size | Train dataset, test dataset, split metadata |
| **Training** | Train Prophet model for a location | Train dataset, model config | Model artifact, training metrics |
| **Evaluation** | Evaluate model on test set, generate plots | Model artifact, test dataset | Metrics, plots, pass/fail decision |
| **Deployment** | Register model to Vertex AI Model Registry, deploy endpoint | Model artifact, evaluation metrics | Endpoint URI |

---

## Component Mapping

How current code maps to Vertex AI components:

| Current Module | Vertex AI Component |
|----------------|---------------------|
| `src/processing/cleaning.py` | `components/data_ingestion/` + `components/preprocessing/` |
| `src/data/splits.py` | `components/preprocessing/` |
| `src/models/prophet_model.py` | `components/training/` |
| `src/models/evaluate.py` | `components/evaluation/` |
| `src/visualization/plots.py` | `components/evaluation/` (or separate reporting component) |
| `src/api/app.py` | `components/deployment/` (registers model endpoint) |

---

## Example Pipeline Definition

### Using KFP v2 Python SDK

```python
# pipelines/training_pipeline.py
from kfp import dsl
from kfp.dsl import Dataset, Model, Metrics, Input, Output
from google.cloud import aiplatform


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "gcsfs"]
)
def ingest_data(
    data_source: str,
    output_dataset: Output[Dataset]
):
    """Load raw data and save to GCS."""
    import pandas as pd
    df = pd.read_csv(data_source)
    df.to_csv(output_dataset.path, index=False)


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy"]
)
def preprocess_and_split(
    input_dataset: Input[Dataset],
    location: str,
    test_size: int,
    train_dataset: Output[Dataset],
    test_dataset: Output[Dataset]
):
    """Prepare location data and split."""
    import pandas as pd
    
    df = pd.read_csv(input_dataset.path)
    
    # Filter for location
    location_df = df[['date', location]].copy()
    location_df.columns = ['ds', 'y']
    location_df['ds'] = pd.to_datetime(location_df['ds'])
    location_df = location_df.dropna().sort_values('ds')
    
    # Split
    train_df = location_df.iloc[:-test_size]
    test_df = location_df.iloc[-test_size:]
    
    train_df.to_csv(train_dataset.path, index=False)
    test_df.to_csv(test_dataset.path, index=False)


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "prophet", "numpy"]
)
def train_model(
    train_dataset: Input[Dataset],
    location: str,
    model_artifact: Output[Model],
    metrics: Output[Metrics]
):
    """Train Prophet model."""
    import pandas as pd
    from prophet import Prophet
    import pickle
    
    train_df = pd.read_csv(train_dataset.path)
    train_df['ds'] = pd.to_datetime(train_df['ds'])
    
    n_days = len(train_df)
    
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=(n_days >= 730),
        interval_width=0.95
    )
    model.fit(train_df)
    
    with open(model_artifact.path, "wb") as f:
        pickle.dump(model, f)
    
    metrics.log_metric("location", location)
    metrics.log_metric("training_days", n_days)


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "prophet", "scikit-learn", "numpy"]
)
def evaluate_model(
    model_artifact: Input[Model],
    test_dataset: Input[Dataset],
    location: str,
    metrics: Output[Metrics]
) -> bool:
    """Evaluate model and decide if deployment-ready."""
    import pickle
    import pandas as pd
    from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
    import numpy as np
    
    with open(model_artifact.path, "rb") as f:
        model = pickle.load(f)
    
    test_df = pd.read_csv(test_dataset.path)
    test_df['ds'] = pd.to_datetime(test_df['ds'])
    
    forecast = model.predict(test_df[['ds']])
    
    rmse = np.sqrt(mean_squared_error(test_df['y'], forecast['yhat']))
    mape = mean_absolute_percentage_error(test_df['y'], forecast['yhat']) * 100
    
    metrics.log_metric("location", location)
    metrics.log_metric("rmse", rmse)
    metrics.log_metric("mape", mape)
    
    # Deployment gate: only deploy if MAPE < 20%
    return mape < 20.0


@dsl.pipeline(
    name="package-forecast-training",
    description="Train Prophet models for package forecasting"
)
def training_pipeline(
    data_source: str = "gs://your-bucket/data.csv",
    locations: list = ["A", "B", "C"],
    test_size: int = 30
):
    """Main training pipeline."""
    ingest_task = ingest_data(data_source=data_source)
    
    for location in locations:
        preprocess_task = preprocess_and_split(
            input_dataset=ingest_task.outputs["output_dataset"],
            location=location,
            test_size=test_size
        )
        
        train_task = train_model(
            train_dataset=preprocess_task.outputs["train_dataset"],
            location=location
        )
        
        eval_task = evaluate_model(
            model_artifact=train_task.outputs["model_artifact"],
            test_dataset=preprocess_task.outputs["test_dataset"],
            location=location
        )
        
        # Conditional deployment based on evaluation
        with dsl.Condition(eval_task.output == True):
            # Add deployment component here
            pass
```

### Compiling and Running the Pipeline

```python
# scripts/run_pipeline.py
from kfp import compiler
from google.cloud import aiplatform
from pipelines.training_pipeline import training_pipeline

# Compile pipeline
compiler.Compiler().compile(
    pipeline_func=training_pipeline,
    package_path="training_pipeline.yaml"
)

# Initialize Vertex AI
aiplatform.init(
    project="your-project-id",
    location="us-central1",
    staging_bucket="gs://your-staging-bucket"
)

# Run pipeline
job = aiplatform.PipelineJob(
    display_name="package-forecast-training",
    template_path="training_pipeline.yaml",
    parameter_values={
        "data_source": "gs://your-bucket/data-4-.csv",
        "locations": ["A", "B", "C"],
        "test_size": 30
    }
)

job.run(sync=True)
```

---

## Key Principles

### 1. Each Pipeline Step = One Component
- Components should be **single-purpose** and **stateless**
- Each component runs in its own container
- Makes debugging, testing, and reuse easier

### 2. Use Artifacts for Data Passing
- Pass **GCS URIs** between components (not raw data in memory)
- Use KFP artifact types: `Dataset`, `Model`, `Metrics`, `Artifact`
- Store intermediate outputs in Cloud Storage

### 3. Containerize Components
- Each component should be self-contained
- Use `@dsl.component` with `packages_to_install` for simple cases
- Use custom Dockerfiles for complex dependencies (like Prophet)

### 4. Externalize Configuration
- No hardcoded paths or values
- Use pipeline parameters for all configurable values
- Store configs in YAML files

### 5. Separate Training from Serving
- Training pipeline: data → model → evaluation
- Inference/batch prediction pipeline: separate pipeline for predictions
- Serving: Deploy to Vertex AI Endpoints or Cloud Run

---

## Migration Steps

### Phase 1: Prepare Shared Code
- [ ] Create `setup.py` to package `src/` as an installable library
- [ ] Externalize all hardcoded paths and configs
- [ ] Add GCS read/write support to data loading functions

### Phase 2: Create Components
- [ ] Create `components/` directory structure
- [ ] Write component code for each step
- [ ] Create Dockerfiles for components with complex dependencies
- [ ] Write `component.yaml` specs (optional, for reusable components)

### Phase 3: Define Pipeline
- [ ] Create `pipelines/training_pipeline.py`
- [ ] Define component DAG and data flow
- [ ] Add conditional logic (e.g., deploy only if evaluation passes)
- [ ] Create `pipelines/inference_pipeline.py` for batch predictions

### Phase 4: Test Locally
- [ ] Test components individually using KFP local runner
- [ ] Test full pipeline using Vertex AI Pipelines in dev project

### Phase 5: Production Setup
- [ ] Set up CI/CD for pipeline deployment
- [ ] Configure pipeline scheduling (Cloud Scheduler)
- [ ] Set up monitoring and alerting
- [ ] Document runbooks and troubleshooting guides

---

## Resources

- [Vertex AI Pipelines Documentation](https://cloud.google.com/vertex-ai/docs/pipelines)
- [Kubeflow Pipelines SDK v2](https://www.kubeflow.org/docs/components/pipelines/v2/)
- [KFP Component Authoring](https://www.kubeflow.org/docs/components/pipelines/v2/author-a-pipeline/components/)
- [Vertex AI Model Registry](https://cloud.google.com/vertex-ai/docs/model-registry/introduction)

---

*Last updated: February 2026*
