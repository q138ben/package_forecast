"""
Forecasting pipeline for generating predictions using trained models.

This module provides functionality to generate forecasts using
pre-trained Prophet models without retraining.
"""
import json
import pickle
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from src.processing.cleaning import load_raw_data, prepare_location_data
from src.visualization.plots import plot_test_period_zoom
from src.models.train import _add_is_weekend




def forecast_location(location: str, 
                     model_path: Optional[str] = None,
                     forecast_days: int = 30,
                     output_dir: str = 'models') -> Dict:
    """
    Generate forecast for a specific location using a trained model.
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        model_path: Path to the trained model pickle file (optional)
        forecast_days: Number of days to forecast into the future
        output_dir: Directory to save forecasts
        
    Returns:
        Dictionary with forecast results and metadata
    """
    print(f"\n{'='*60}")
    print(f"Generating forecast for Location {location}")
    print(f"{'='*60}")
    
    # Load the trained model
    if model_path is None:
        model_path = Path(output_dir) / f'location_{location}_model.pkl'
    else:
        model_path = Path(model_path)
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}. "
            f"Please train the model first using 'python main.py train'"
        )
    
    print(f"Loading model from: {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Generate future dataframe
    future = model.make_future_dataframe(periods=forecast_days)
    
    # Add weekend features
    future = _add_is_weekend(future)
    
    # Generate forecast
    print(f"Generating {forecast_days}-day forecast...")
    full_forecast = model.predict(future)
    
    # Extract only future forecast (not historical)
    future_forecast = full_forecast.tail(forecast_days)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    future_forecast.columns = ['date', 'forecast', 'lower_bound', 'upper_bound']
    
    # Ensure non-negative forecasts (packages can't be negative)
    for col in ['forecast', 'lower_bound', 'upper_bound']:
        future_forecast[col] = future_forecast[col].clip(lower=0)
    
    # Save forecast
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    forecast_file = output_path / f'location_{location}_forecast.csv'
    future_forecast.to_csv(forecast_file, index=False)
    
    # Generate visualization comparing test period predictions
    # Load test data for visualization
    test_data_file = output_path / f'location_{location}_test_data.csv'
    if test_data_file.exists():
        print(f"Generating visualization...")
        test_df = pd.read_csv(test_data_file)
        test_df['ds'] = pd.to_datetime(test_df['ds'])
        plot_file = plot_test_period_zoom(location, test_df, full_forecast, output_dir)
    else:
        print(f"Warning: Test data not found at {test_data_file}. Skipping visualization.")
        plot_file = None
    
    # Calculate summary statistics
    forecast_stats = {
        'location': location,
        'forecast_days': forecast_days,
        'start_date': future_forecast['date'].min().strftime('%Y-%m-%d'),
        'end_date': future_forecast['date'].max().strftime('%Y-%m-%d'),
        'mean_forecast': float(future_forecast['forecast'].mean()),
        'total_forecast': float(future_forecast['forecast'].sum()),
        'min_forecast': float(future_forecast['forecast'].min()),
        'max_forecast': float(future_forecast['forecast'].max()),
        'forecast_file': str(forecast_file)
    }
    
    if plot_file:
        forecast_stats['plot_file'] = plot_file
    
    print(f"\nForecast Summary:")
    print(f"  Period: {forecast_stats['start_date']} to {forecast_stats['end_date']}")
    print(f"  Mean daily forecast: {forecast_stats['mean_forecast']:.1f} packages")
    print(f"  Total forecast: {forecast_stats['total_forecast']:.0f} packages")
    print(f"  Range: {forecast_stats['min_forecast']:.1f} - {forecast_stats['max_forecast']:.1f} packages")
    print(f"  Saved to: {forecast_file}")
    
    return forecast_stats


def forecast_all_locations(output_dir: str = 'models',
                          locations: list = None,
                          forecast_days: int = 30) -> Dict:
    """
    Generate forecasts for all specified locations.
    
    Args:
        output_dir: Directory containing trained models and to save forecasts
        locations: List of location identifiers (default: ['A', 'B', 'C'])
        forecast_days: Number of days to forecast into the future
        
    Returns:
        Dictionary with forecast results for all locations
    """
    if locations is None:
        locations = ['A', 'B', 'C']
    
    all_forecasts = {}
    
    for location in locations:
        try:
            forecast_stats = forecast_location(
                location, 
                output_dir=output_dir,
                forecast_days=forecast_days
            )
            all_forecasts[location] = forecast_stats
        except Exception as e:
            print(f"\n❌ Error forecasting location {location}: {e}")
            all_forecasts[location] = {'error': str(e)}
    
    print(f"\n{'='*60}")
    print("Forecasting Complete!")
    print(f"{'='*60}")
    
    return all_forecasts


if __name__ == '__main__':
    results = forecast_all_locations()
