# Technical Plan & Approach

## 1. Problem Understanding
The goal is to forecast daily package volumes for three locations (A, B, C) for the next 30 days and serve these via an API.
Key challenges include handling potential missing data and "cold start" issues for specific locations.

## 2. Evaluation Points Strategy

### Data Exploration & Insights
- **Input**: `data-4-.csv`.
- **Finding (Location C)**: Exploration has revealed that Location C is **highly sparse** before September 2024.
    - *Strategy*: We cannot treat Location C the same as A and B. Imputing 2.5 years of zeros would bias the model.
    - *Action*: We will dynamically determine the "start of valid data" for each location. For C, the model will only be trained on data from ~Sep 2024 onwards.
- **Seasonality**:
    - Locations A & B: Likely have strong yearly and weekly seasonality (vacations, weekends).
    - Location C: With <1 year of data, yearly seasonality will be hard to estimate. We will rely primarily on weekly seasonality and trend.

### Modeling Approach
- **Model Choice**: **Facebook Prophet**.
    - *Why?*
        - Handles missing data natively.
        - Robust to outliers and trend shifts.
        - Provides "uncertainty intervals" (Bonus requirement).
    - *Configuration*:
        - **A & B**: Enable `yearly_seasonality` and `weekly_seasonality`.
        - **C**: Enable `weekly_seasonality`. Disable `yearly_seasonality` (or set to auto with low prior) to avoid overfitting the short history.
- **Granularity**: Separate models for Locations A, B, and C (“Local Forecasting”).
    - *Justification*: The "Start Date" difference alone necessitates separate training pipelines.
- **Evaluation Metrics**:
    - **RMSE (Root Mean Squared Error)**: To penalize large volume spikes/drops.
    - **MAPE (Mean Absolute Percentage Error)**: For business-friendly accuracy reporting.
- **Validation Strategy**:
    - Split: Train on `Start` to `T-30 days`. Validate on last 30 days.

### Forecast Generation
- **Horizon**: 30 Days.
- **Output**: Daily values.
- **Bonus**: Include `yhat_lower` and `yhat_upper` columns as metrics of certainty.

### API Architecture
- **Framework**: **FastAPI**.
    - *Why?* High performance, async, automatic Swagger/OpenAPI documentation.
- **Usage**: `GET /forecast/{location_id}`.
- **Deployment**:
    - **Dockerized**: A `Dockerfile` will be provided for stateless deployment (e.g., Google Cloud Run).
    - **Structure**: Pre-trained models will be loaded on startup for low-latency inference.

## 3. Project Structure
```text
package_forecast/
├── data/               # Raw data
├── docs/               # Documentation
├── src/
│   ├── api/            # FastAPI app
│   ├── models/         # Training logic & Prophet wrappers
│   ├── processing/     # Data cleaning & "Start Date" detection
│   └── __init__.py
├── notebooks/          # Exploratory Data Analysis (EDA)
├── Dockerfile          # For cloud deployment
├── requirements.txt    # Dependencies
└── main.py             # Entry point
```
