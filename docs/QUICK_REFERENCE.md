# Quick Reference

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Train models
python main.py train

# Start API server
python main.py serve

# Run with Docker
docker build -t package-forecast-api .
docker run -p 8000:8000 package-forecast-api
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/forecast/{location}` | GET | Get forecast for location A, B, or C |
| `/forecasts/all` | GET | Get forecasts for all locations |
| `/docs` | GET | Interactive Swagger documentation |

## Example Requests

```bash
# Get forecast for Location A
curl http://localhost:8000/forecast/A

# Get all forecasts
curl http://localhost:8000/forecasts/all

# Health check
curl http://localhost:8000/health
```

## Response Format

```json
{
  "location": "A",
  "forecast_generated": "2026-02-09T10:30:00",
  "horizon_days": 30,
  "forecasts": [
    {
      "date": "2026-02-10",
      "forecast": 20338.88,
      "lower_bound": 12349.47,
      "upper_bound": 27336.77
    }
  ]
}
```

## Files Overview

| File | Purpose |
|------|---------|
| `main.py` | Entry point (train/serve) |
| `src/processing/cleaning.py` | Data loading & preprocessing |
| `src/models/train.py` | Model training pipeline |
| `src/api/app.py` | FastAPI application |
| `notebooks/EDA.ipynb` | Exploratory data analysis |
| `docs/MODEL_EXPLANATION.md` | Model selection rationale |
| `docs/DEPLOYMENT.md` | Cloud deployment guide |
| `models/location_X_forecast.csv` | Generated forecasts |

## Key Design Decisions

1. **Separate Models**: Each location gets its own model due to different data availability and patterns
2. **Prophet**: Chosen for built-in seasonality handling and uncertainty intervals
3. **FastAPI**: Modern, fast, with auto-generated documentation
4. **Docker**: Containerized for easy deployment to any cloud provider

## Troubleshooting

**Import errors**: Run `pip install -r requirements.txt`

**Port already in use**: Change port with `uvicorn src.api.app:app --port 8001`

**Models not found**: Run `python main.py train` first

**High MAPE values**: Expected when test data contains near-zero values. RMSE is the primary metric.

## Model Performance

| Location | RMSE | Avg Daily Volume | Relative Error |
|----------|------|------------------|----------------|
| A | 5,944.71 | 13,763.8 | ~43% |
| B | 3,153.54 | 5,610.1 | ~56% |
| C | 1,538.34 | 4,401.3 | ~35% |

## Project Status: ✅ Complete

All requirements and bonus features implemented:
- ✅ Data exploration
- ✅ Model training (A, B, and C)
- ✅ Uncertainty intervals
- ✅ API implementation
- ✅ Docker deployment ready
- ✅ Clear documentation
