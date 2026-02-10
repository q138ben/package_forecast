"""
FastAPI application for serving package forecasts.

This API exposes forecasts for three logistics locations (A, B, C).
Each endpoint returns 30-day predictions with uncertainty intervals.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from pathlib import Path
from datetime import datetime

app = FastAPI(
    title="Package Forecast API",
    description="30-day package volume forecasts for logistics locations A, B, and C",
    version="1.0.0"
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
    forecast_file = Path('models') / f'location_{location}_forecast.csv'
    
    if not forecast_file.exists():
        raise FileNotFoundError(f"Forecast for location {location} not found")
    
    df = pd.read_csv(forecast_file)
    return df


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Package Forecast API",
        "version": "1.0.0",
        "endpoints": {
            "/forecast/{location}": "Get 30-day forecast for a location (A, B, or C)",
            "/health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/forecast/{location}", response_model=ForecastResponse)
async def get_forecast(location: str):
    """
    Get 30-day package forecast for a specific location.
    
    Args:
        location: Location identifier (A, B, or C)
        
    Returns:
        Forecast data with daily predictions and uncertainty intervals
        
    Example:
        GET /forecast/A
    """
    # Validate location
    location = location.upper()
    if location not in ['A', 'B', 'C']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid location '{location}'. Must be A, B, or C."
        )
    
    # Load forecast
    try:
        forecast_df = load_forecast(location)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Forecast for location {location} not found. Please run training first."
        )
    
    # Convert to response format
    forecasts = []
    for _, row in forecast_df.iterrows():
        forecasts.append(ForecastPoint(
            date=row['date'],
            forecast=round(row['forecast'], 2),
            lower_bound=round(row['lower_bound'], 2),
            upper_bound=round(row['upper_bound'], 2)
        ))
    
    return ForecastResponse(
        location=location,
        forecast_generated=datetime.now().isoformat(),
        horizon_days=len(forecasts),
        forecasts=forecasts
    )


@app.get("/forecasts/all")
async def get_all_forecasts():
    """
    Get forecasts for all locations (A, B, and C).
    
    Returns:
        Dictionary with forecasts for all available locations
    """
    results = {}
    
    for location in ['A', 'B', 'C']:
        try:
            forecast_df = load_forecast(location)
            
            forecasts = []
            for _, row in forecast_df.iterrows():
                forecasts.append({
                    'date': row['date'],
                    'forecast': round(row['forecast'], 2),
                    'lower_bound': round(row['lower_bound'], 2),
                    'upper_bound': round(row['upper_bound'], 2)
                })
            
            results[location] = {
                'location': location,
                'horizon_days': len(forecasts),
                'forecasts': forecasts
            }
        except FileNotFoundError:
            results[location] = {
                'error': f'Forecast not available for location {location}'
            }
    
    return {
        'forecast_generated': datetime.now().isoformat(),
        'locations': results
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
