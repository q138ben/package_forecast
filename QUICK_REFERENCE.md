# Package Forecast Quick Reference

## 1. Data EDA
- Open and explore data in `notebooks/EDA.ipynb`

## 2. Train Forecasting Models
```
python main.py train
```
- Trains models for all locations
- Artifacts saved in `artifacts/`

## 3. Generate Forecasts
```
python main.py forecast
```
- Generates forecasts using trained models
- Forecasts saved in `artifacts/`

## 4. Run API Locally
```
python main.py serve
```
- API docs: http://localhost:8000/docs

## 5. Deploy with gcloud
```
./scripts/deploy_gcp.sh [PROJECT_ID]
```

