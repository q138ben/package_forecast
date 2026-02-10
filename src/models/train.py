"""
Training pipeline for location-specific Prophet models.

This module trains separate forecasting models for each location (A, B, C)
with appropriate seasonality configuration based on data availability.
"""
import json
import pickle
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
import numpy as np

from src.processing.cleaning import load_raw_data, prepare_location_data


def create_prophet_model(location: str, n_days: int) -> Prophet:
    """
    Create a Prophet model with location-specific configuration.
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        n_days: Number of days of historical data available
        
    Returns:
        Configured Prophet model (not yet fitted)
    """
    # Base configuration
    model = Prophet(
        daily_seasonality=False,  # We're dealing with daily aggregates
        weekly_seasonality=True,
        interval_width=0.95  # 95% confidence intervals
    )
    
    # For locations with <2 years of data, disable yearly seasonality
    # to avoid overfitting. Location C only has data from Sep 2024.
    if n_days < 730:  # Less than 2 years
        model.yearly_seasonality = False
        print(f"Location {location}: Disabled yearly seasonality (only {n_days} days)")
    else:
        model.yearly_seasonality = True
        print(f"Location {location}: Enabled yearly seasonality ({n_days} days)")
    
    return model


def evaluate_model(model: Prophet, test_df: pd.DataFrame) -> Dict[str, float]:
    """
    Evaluate model performance on test data.
    
    Args:
        model: Fitted Prophet model
        test_df: Test dataframe with 'ds' and 'y' columns
        
    Returns:
        Dictionary with RMSE and MAPE metrics
    """
    # Generate predictions for test period
    forecast = model.predict(test_df[['ds']])
    
    # Calculate metrics
    rmse = np.sqrt(mean_squared_error(test_df['y'], forecast['yhat']))
    mape = mean_absolute_percentage_error(test_df['y'], forecast['yhat']) * 100
    
    return {
        'rmse': float(rmse),
        'mape': float(mape)
    }


def train_location_model(location: str, data_path: str, 
                        output_dir: str = 'models') -> Dict:
    """
    Train a Prophet model for a specific location.
    
    This function:
    1. Loads and prepares data for the location
    2. Splits into train/validation (last 30 days for validation)
    3. Trains the model
    4. Evaluates performance
    5. Retrains on full data and generates 30-day forecast
    6. Saves model and forecast
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        data_path: Path to the raw CSV data
        output_dir: Directory to save trained models and forecasts
        
    Returns:
        Dictionary with training results and metrics
    """
    print(f"\n{'='*60}")
    print(f"Training model for Location {location}")
    print(f"{'='*60}")
    
    # Load and prepare data
    df = load_raw_data(data_path)
    location_df, metadata = prepare_location_data(df, location)
    
    print(f"\nData Summary:")
    print(f"  Date range: {metadata['start_date']} to {metadata['end_date']}")
    print(f"  Total days: {metadata['n_days']}")
    print(f"  Mean packages: {metadata['mean_packages']:.1f}")
    print(f"  Std packages: {metadata['std_packages']:.1f}")
    
    # Split into train/test (last 30 days for validation)
    train_df = location_df.iloc[:-30].copy()
    test_df = location_df.iloc[-30:].copy()
    
    print(f"\nTrain/Test Split:")
    print(f"  Train: {len(train_df)} days")
    print(f"  Test: {len(test_df)} days")
    
    # Create and train model on training data
    model = create_prophet_model(location, len(train_df))
    model.fit(train_df)
    
    # Evaluate on validation set
    metrics = evaluate_model(model, test_df)
    print(f"\nValidation Performance:")
    print(f"  RMSE: {metrics['rmse']:.2f} packages")
    print(f"  MAPE: {metrics['mape']:.2f}%")
    
    # Retrain on full dataset for production forecast
    print(f"\nRetraining on full dataset...")
    final_model = create_prophet_model(location, len(location_df))
    final_model.fit(location_df)
    
    # Generate 30-day future forecast
    future = final_model.make_future_dataframe(periods=30)
    forecast = final_model.predict(future)
    
    # Extract only the future 30 days
    future_forecast = forecast.tail(30)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    future_forecast.columns = ['date', 'forecast', 'lower_bound', 'upper_bound']
    
    # Ensure non-negative forecasts (packages can't be negative)
    for col in ['forecast', 'lower_bound', 'upper_bound']:
        future_forecast[col] = future_forecast[col].clip(lower=0)
    
    # Save artifacts
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save the trained model
    model_file = output_path / f'location_{location}_model.pkl'
    with open(model_file, 'wb') as f:
        pickle.dump(final_model, f)
    
    # Save the forecast
    forecast_file = output_path / f'location_{location}_forecast.csv'
    future_forecast.to_csv(forecast_file, index=False)
    
    # Save metadata and metrics
    results = {
        'location': location,
        'metadata': metadata,
        'metrics': metrics,
        'forecast_file': str(forecast_file),
        'model_file': str(model_file)
    }
    
    results_file = output_path / f'location_{location}_results.json'
    with open(results_file, 'w') as f:
        # Convert datetime to string for JSON serialization
        results_copy = results.copy()
        results_copy['metadata']['start_date'] = results_copy['metadata']['start_date'].strftime('%Y-%m-%d')
        results_copy['metadata']['end_date'] = results_copy['metadata']['end_date'].strftime('%Y-%m-%d')
        json.dump(results_copy, f, indent=2)
    
    print(f"\nSaved:")
    print(f"  Model: {model_file}")
    print(f"  Forecast: {forecast_file}")
    print(f"  Results: {results_file}")
    
    return results


def train_all_locations(data_path: str = 'data-4-.csv', 
                       output_dir: str = 'models') -> Dict:
    """
    Train models for all three locations (A, B, C).
    
    Args:
        data_path: Path to the raw CSV data
        output_dir: Directory to save trained models and forecasts
        
    Returns:
        Dictionary with results for all locations
    """
    locations = ['A', 'B', 'C']
    all_results = {}
    
    for location in locations:
        try:
            results = train_location_model(location, data_path, output_dir)
            all_results[location] = results
        except Exception as e:
            print(f"\n❌ Error training location {location}: {e}")
            all_results[location] = {'error': str(e)}
    
    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    
    return all_results


if __name__ == '__main__':
    # Run training pipeline
    results = train_all_locations()
