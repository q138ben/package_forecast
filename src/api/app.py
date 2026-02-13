"""
FastAPI application for serving package forecasts.

This API exposes forecasts for three logistics locations (A, B, C).
Each endpoint returns 30-day predictions with uncertainty intervals.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


def get_artifacts_dir():
    return os.environ.get("ARTIFACTS_DIR", "artifacts")


app = FastAPI(
    title="Package Forecast API",
    description="30-day package volume forecasts for logistics locations A, B, and C",
    version="1.0.0",
)


class ForecastPoint(BaseModel):
    """Single day forecast with uncertainty bounds."""

    date: str
    forecast: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    """Response model for forecast endpoint."""

    location: str
    forecast_generated: str
    horizon_days: int
    forecasts: List[ForecastPoint]


def load_forecast(location: str) -> pd.DataFrame:
    """
    Load pre-computed forecast for a location.

    Args:
        location: Location identifier ('A', 'B', or 'C')

    Returns:
        DataFrame with forecast data

    Raises:
        FileNotFoundError: If forecast file doesn't exist
    """
    # Use absolute path based on this file's location
    # This works both locally and in Docker/Cloud Run
    base_dir = Path(__file__).resolve().parent.parent.parent
    artifacts_dir = get_artifacts_dir()
    forecast_file = base_dir / artifacts_dir / f"location_{location}_forecast.csv"

    if not forecast_file.exists():
        raise FileNotFoundError(f"Forecast for location {location} not found")

    df = pd.read_csv(forecast_file)
    return df


@app.get("/")
async def root(location: Optional[str] = None, date: Optional[str] = None):
    """
    Root endpoint returns forecasts for all locations.

    Query Parameters:
        location: Optional filter by location (A, B, or C)
        date: Optional filter by date (format: YYYY-MM-DD)

    Examples:
        GET /
        GET /?location=A
        GET /?date=2026-02-15
        GET /?location=A&date=2026-02-15
    """
    # Determine which locations to fetch
    if location:
        location = location.upper()
        if location not in ["A", "B", "C"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid location '{location}'. Must be A, B, or C.",
            )
        locations_to_fetch = [location]
    else:
        locations_to_fetch = ["A", "B", "C"]

    results = {}

    for loc in locations_to_fetch:
        try:
            forecast_df = load_forecast(loc)

            # Filter by date if provided
            if date:
                forecast_df = forecast_df[forecast_df["date"] == date]
                if forecast_df.empty:
                    results[loc] = {"error": f"No forecast found for date {date}"}
                    continue

            forecasts = []
            for _, row in forecast_df.iterrows():
                forecasts.append(
                    {
                        "date": row["date"],
                        "forecast": round(row["forecast"], 2),
                        "lower_bound": round(row["lower_bound"], 2),
                        "upper_bound": round(row["upper_bound"], 2),
                    }
                )

            results[loc] = {"horizon_days": len(forecasts), "forecasts": forecasts}
        except FileNotFoundError:
            results[loc] = {"error": f"Forecast not available for location {loc}"}

    return {
        "forecast_generated": datetime.now().isoformat(),
        "filters": {"location": location, "date": date},
        "locations": results,
    }


@app.get("/health")
async def health():
    """Health check endpoint (liveness)."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/ready")
async def ready():
    """
    Readiness check endpoint.

    Verifies the app is ready to serve requests by checking
    if forecast data is available for all locations.
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    artifacts_dir = get_artifacts_dir()
    missing = []
    for location in ["A", "B", "C"]:
        forecast_file = base_dir / artifacts_dir / f"location_{location}_forecast.csv"
        if not forecast_file.exists():
            missing.append(location)

    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Not ready: missing forecasts for locations {missing}",
        )

    return {"status": "ready", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
