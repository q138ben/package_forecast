# Package Forecasting Service

This project provides an automated forecasting solution for daily package volumes at three logistics locations. It includes data analysis, machine learning modeling, and a REST API to expose predictions. Avoid "AI-generated looking code" (keep it simple, idiomatic, and well-commented).

## Overview

- **Goal**: Predict 30-day package volume for Locations A, B, and C.
- **Stack**: Python, Prophet, FastAPI, Pandas, Docker.
- **Status**: ✅ Complete - All requirements and bonus features implemented.

## What's Included

✅ **Data Exploration**: Comprehensive EDA in Jupyter notebook  
✅ **Forecasting Models**: Prophet models for all 3 locations (A, B, C)  
✅ **Uncertainty Estimates**: 95% confidence intervals (bonus)  
✅ **API Implementation**: FastAPI with auto-generated docs  
✅ **Cloud Ready**: Dockerfile + GCP deployment guide (bonus)  
✅ **Clean Code**: Well-structured, commented, production-ready

## Features

- **Automated Forecasting**: Uses time-series models (Prophet) to handle seasonality and trends.
- **Uncertainty Estimates**: Provides upper and lower bounds for predictions (Bonus).
- **API Access**: RESTful implementation using FastAPI.
- **Container Ready**: Dockerized for easy deployment to GCP/AWS (Bonus).

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Explore the Data (Optional)
Open the Jupyter notebook to visualize the data:
```bash
jupyter notebook notebooks/EDA.ipynb
```

### 3. Train Models
Train forecasting models for all three locations:
```bash
python main.py train
```

This will:
- Load and clean the data
- Train separate Prophet models for locations A, B, and C
- Evaluate performance using RMSE and MAPE
- Generate 30-day forecasts with uncertainty intervals
- Save models and forecasts to `models/` directory

### 4. Start the API
Launch the FastAPI server:
```bash
python main.py serve
```

The API will be available at `http://localhost:8000`

### 5. Access Forecasts
- **Interactive docs**: http://localhost:8000/docs
- **Single location**: `GET /forecast/A` (or B, C)
- **All locations**: `GET /forecasts/all`

Example response:
```json
{
  "location": "A",
  "forecast_generated": "2026-02-09T10:30:00",
  "horizon_days": 30,
  "forecasts": [
    {
      "date": "2026-02-10",
      "forecast": 1250.5,
      "lower_bound": 1100.2,
      "upper_bound": 1400.8
    }
  ]
}
```

## Docker Deployment

Build and run the containerized API:
```bash
# Build image
docker build -t package-forecast-api .

# Run container
docker run -p 8000:8000 package-forecast-api
```

For cloud deployment (GCP Cloud Run):
```bash
# Tag and push to registry
docker tag package-forecast-api gcr.io/YOUR-PROJECT/package-forecast-api
docker push gcr.io/YOUR-PROJECT/package-forecast-api

# Deploy to Cloud Run
gcloud run deploy package-forecast-api \
  --image gcr.io/YOUR-PROJECT/package-forecast-api \
  --platform managed \
  --region us-central1
```

## Documentation

See [docs/PLAN.md](docs/PLAN.md) for the detailed technical approach and architectural decisions.
