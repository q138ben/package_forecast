"""
Training pipeline for location-specific Prophet models.

This module trains separate forecasting models for each location (A, B, C)
with appropriate seasonality configuration based on data availability.
"""
import json
import pickle
from pathlib import Path
from typing import Dict, Tuple, List

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


def time_series_cv_split(df: pd.DataFrame, n_folds: int = 5, 
                         test_size: int = 30, gap: int = 0) -> List[Dict]:
    """
    Create time series cross-validation splits.
    
    Unlike regular k-fold CV, time series CV respects temporal ordering:
    - Training data is always before validation data
    - Each fold expands the training window
    
    Args:
        df: DataFrame with time series data (must have 'ds' column)
        n_folds: Number of CV folds
        test_size: Number of days in each validation fold
        gap: Number of days between train and validation (to prevent leakage)
        
    Returns:
        List of dicts containing train/val indices and date ranges
    """
    n_samples = len(df)
    
    # Reserve last test_size days for final holdout test
    # CV is done on the remaining data
    cv_end_idx = n_samples - test_size
    
    # Calculate minimum training size (at least 2x test_size)
    min_train_size = test_size * 2
    
    # Calculate the step size between folds
    available_for_cv = cv_end_idx - min_train_size - gap
    fold_step = available_for_cv // n_folds
    
    splits = []
    
    for fold in range(n_folds):
        # Training end index grows with each fold
        train_end_idx = min_train_size + (fold * fold_step)
        
        # Validation starts after the gap
        val_start_idx = train_end_idx + gap
        val_end_idx = min(val_start_idx + test_size, cv_end_idx)
        
        # Ensure we have enough validation data
        if val_end_idx - val_start_idx < test_size // 2:
            continue
            
        split_info = {
            'fold': fold + 1,
            'train_idx': (0, train_end_idx),
            'val_idx': (val_start_idx, val_end_idx),
            'train_dates': (df.iloc[0]['ds'].strftime('%Y-%m-%d'), 
                          df.iloc[train_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'val_dates': (df.iloc[val_start_idx]['ds'].strftime('%Y-%m-%d'),
                         df.iloc[val_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'train_size': train_end_idx,
            'val_size': val_end_idx - val_start_idx
        }
        splits.append(split_info)
    
    return splits


def run_time_series_cv(location: str, df: pd.DataFrame, 
                       n_folds: int = 5, test_size: int = 30) -> Dict:
    """
    Run time series cross-validation for a location.
    
    Args:
        location: Location identifier
        df: Full location dataframe (without final test holdout)
        n_folds: Number of CV folds
        test_size: Size of each validation fold
        
    Returns:
        Dictionary with CV results and metrics per fold
    """
    splits = time_series_cv_split(df, n_folds=n_folds, test_size=test_size)
    
    cv_results = {
        'n_folds': len(splits),
        'folds': [],
        'avg_rmse': 0.0,
        'avg_mape': 0.0,
        'std_rmse': 0.0,
        'std_mape': 0.0
    }
    
    all_rmse = []
    all_mape = []
    
    print(f"\n  Running {len(splits)}-fold Time Series Cross-Validation...")
    
    for split in splits:
        fold = split['fold']
        train_start, train_end = split['train_idx']
        val_start, val_end = split['val_idx']
        
        train_df = df.iloc[train_start:train_end].copy()
        val_df = df.iloc[val_start:val_end].copy()
        
        # Train model on this fold
        model = create_prophet_model(location, len(train_df))
        model.fit(train_df)
        
        # Evaluate
        metrics = evaluate_model(model, val_df)
        
        fold_result = {
            **split,
            'metrics': metrics
        }
        cv_results['folds'].append(fold_result)
        
        all_rmse.append(metrics['rmse'])
        all_mape.append(metrics['mape'])
        
        print(f"    Fold {fold}: Train {split['train_dates'][0]} to {split['train_dates'][1]} "
              f"| Val {split['val_dates'][0]} to {split['val_dates'][1]} "
              f"| RMSE: {metrics['rmse']:.2f} | MAPE: {metrics['mape']:.2f}%")
    
    # Calculate aggregate metrics
    cv_results['avg_rmse'] = float(np.mean(all_rmse))
    cv_results['avg_mape'] = float(np.mean(all_mape))
    cv_results['std_rmse'] = float(np.std(all_rmse))
    cv_results['std_mape'] = float(np.std(all_mape))
    
    print(f"\n  CV Summary: RMSE = {cv_results['avg_rmse']:.2f} ± {cv_results['std_rmse']:.2f} | "
          f"MAPE = {cv_results['avg_mape']:.2f}% ± {cv_results['std_mape']:.2f}%")
    
    return cv_results


def save_data_splits(location: str, train_df: pd.DataFrame, test_df: pd.DataFrame,
                    cv_results: Dict, output_dir: str = 'models') -> str:
    """
    Save train/test split and CV fold information for reproducibility.
    
    Args:
        location: Location identifier
        train_df: Training dataframe (excluding final test)
        test_df: Final test holdout dataframe
        cv_results: Cross-validation results with fold information
        output_dir: Directory to save splits
        
    Returns:
        Path to saved splits file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    splits_info = {
        'location': location,
        'created_at': pd.Timestamp.now().isoformat(),
        'final_split': {
            'train': {
                'start_date': train_df.iloc[0]['ds'].strftime('%Y-%m-%d'),
                'end_date': train_df.iloc[-1]['ds'].strftime('%Y-%m-%d'),
                'n_samples': len(train_df)
            },
            'test': {
                'start_date': test_df.iloc[0]['ds'].strftime('%Y-%m-%d'),
                'end_date': test_df.iloc[-1]['ds'].strftime('%Y-%m-%d'),
                'n_samples': len(test_df)
            }
        },
        'cv_folds': cv_results['folds']
    }
    
    # Save as JSON
    splits_file = output_path / f'location_{location}_splits.json'
    with open(splits_file, 'w') as f:
        json.dump(splits_info, f, indent=2)
    
    # Also save train/test data as CSV for easy access
    train_file = output_path / f'location_{location}_train_data.csv'
    test_file = output_path / f'location_{location}_test_data.csv'
    
    train_df.to_csv(train_file, index=False)
    test_df.to_csv(test_file, index=False)
    
    return str(splits_file)


def train_location_model(location: str, data_path: str, 
                        output_dir: str = 'models',
                        n_cv_folds: int = 5) -> Dict:
    """
    Train a Prophet model for a specific location.
    
    This function:
    1. Loads and prepares data for the location
    2. Holds out last 30 days as final test set
    3. Runs n-fold time series cross-validation on remaining data
    4. Evaluates on final test set
    5. Retrains on full data and generates 30-day forecast
    6. Saves model, forecast, and data splits
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        data_path: Path to the raw CSV data
        output_dir: Directory to save trained models and forecasts
        n_cv_folds: Number of cross-validation folds
        
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
    
    # Split into train/test (last 30 days held out for final test)
    train_df = location_df.iloc[:-30].copy()
    test_df = location_df.iloc[-30:].copy()
    
    print(f"\nFinal Train/Test Split:")
    print(f"  Train: {len(train_df)} days ({train_df.iloc[0]['ds'].strftime('%Y-%m-%d')} to {train_df.iloc[-1]['ds'].strftime('%Y-%m-%d')})")
    print(f"  Test (holdout): {len(test_df)} days ({test_df.iloc[0]['ds'].strftime('%Y-%m-%d')} to {test_df.iloc[-1]['ds'].strftime('%Y-%m-%d')})")
    
    # Run time series cross-validation on training data
    cv_results = run_time_series_cv(location, train_df, n_folds=n_cv_folds, test_size=30)
    
    # Train model on full training data (excluding test holdout)
    print(f"\n  Training model on full training data...")
    model = create_prophet_model(location, len(train_df))
    model.fit(train_df)
    
    # Evaluate on final test holdout
    test_metrics = evaluate_model(model, test_df)
    print(f"\nFinal Test Performance (Holdout):")
    print(f"  RMSE: {test_metrics['rmse']:.2f} packages")
    print(f"  MAPE: {test_metrics['mape']:.2f}%")
    
    # Save data splits for reproducibility
    splits_file = save_data_splits(location, train_df, test_df, cv_results, output_dir)
    
    # Retrain on full dataset for production forecast
    print(f"\nRetraining on full dataset for production...")
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
        'cv_metrics': {
            'avg_rmse': cv_results['avg_rmse'],
            'avg_mape': cv_results['avg_mape'],
            'std_rmse': cv_results['std_rmse'],
            'std_mape': cv_results['std_mape'],
            'n_folds': cv_results['n_folds']
        },
        'test_metrics': test_metrics,
        'forecast_file': str(forecast_file),
        'model_file': str(model_file),
        'splits_file': splits_file
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
    print(f"  Splits: {splits_file}")
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
