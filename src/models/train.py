"""
Training pipeline for location-specific Prophet models.

This module orchestrates the training process by coordinating
data loading, model training, evaluation, and artifact saving.
"""
import json
import pickle
from pathlib import Path
from typing import Dict

import pandas as pd

from src.processing.cleaning import load_raw_data, prepare_location_data
from src.models.prophet_model import create_prophet_model
from src.models.evaluate import (
    evaluate_model,
    evaluate_naive_baseline,
    run_time_series_cv,
)
from src.data.splits import split_train_test, save_data_splits
from src.visualization.plots import plot_forecast_vs_actual


def train_location_model(location: str, data_path: str, 
                        output_dir: str = 'models',
                        n_cv_folds: int = 5,
                        test_size: int = 30) -> Dict:
    """
    Train a Prophet model for a specific location.
    
    This function orchestrates the full training pipeline:
    1. Loads and prepares data for the location
    2. Holds out last 30 days as final test set
    3. Runs n-fold time series cross-validation on remaining data
    4. Evaluates on final test set
    5. Retrains on full data and generates 30-day forecast
    6. Saves model, forecast, data splits, and visualizations
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        data_path: Path to the raw CSV data
        output_dir: Directory to save trained models and forecasts
        n_cv_folds: Number of cross-validation folds
        test_size: Number of days to hold out for testing
        
    Returns:
        Dictionary with training results and metrics
    """
    print(f"\n{'='*60}")
    print(f"Training model for Location {location}")
    print(f"{'='*60}")
    
    # Step 1: Load and prepare data
    df = load_raw_data(data_path)
    location_df, metadata = prepare_location_data(df, location)
    
    print(f"\nData Summary:")
    print(f"  Date range: {metadata['start_date']} to {metadata['end_date']}")
    print(f"  Total days: {metadata['n_days']}")
    print(f"  Mean packages: {metadata['mean_packages']:.1f}")
    print(f"  Std packages: {metadata['std_packages']:.1f}")
    
    # Step 2: Split into train/test
    train_df, test_df = split_train_test(location_df, test_size=test_size)
    
    print(f"\nFinal Train/Test Split:")
    print(f"  Train: {len(train_df)} days ({train_df.iloc[0]['ds'].strftime('%Y-%m-%d')} to {train_df.iloc[-1]['ds'].strftime('%Y-%m-%d')})")
    print(f"  Test (holdout): {len(test_df)} days ({test_df.iloc[0]['ds'].strftime('%Y-%m-%d')} to {test_df.iloc[-1]['ds'].strftime('%Y-%m-%d')})")
    
    # Step 3: Run time series cross-validation on training data
    cv_results = run_time_series_cv(location, train_df, n_folds=n_cv_folds, test_size=test_size)
    
    # Step 4: Train model on full training data and evaluate on test
    print(f"\n  Training model on full training data...")
    model = create_prophet_model(location, len(train_df))
    model.fit(train_df)
    
    test_metrics = evaluate_model(model, test_df)
    baseline_test_metrics = evaluate_naive_baseline(train_df, test_df)
    print(f"\nFinal Test Performance (Holdout):")
    print(f"  RMSE: {test_metrics['rmse']:.2f} packages")
    print(f"  MAE: {test_metrics['mae']:.2f} packages")
    print(f"  WAPE: {test_metrics['wape']:.2f}%")
    print(f"  Interval coverage: {test_metrics['interval_coverage']:.1f}%")
    print(
        f"  Baseline (seasonal naive): RMSE={baseline_test_metrics['rmse']:.2f}, "
        f"MAE={baseline_test_metrics['mae']:.2f}, WAPE={baseline_test_metrics['wape']:.2f}% "
        f"Coverage={baseline_test_metrics['interval_coverage']:.1f}%"
    )
    
    # Step 5: Save data splits for reproducibility
    splits_file = save_data_splits(location, train_df, test_df, cv_results, output_dir)
    
    # Step 6: Retrain on full dataset for production forecast
    print(f"\nRetraining on full dataset for production...")
    final_model = create_prophet_model(location, len(location_df))
    final_model.fit(location_df)
    
    # Step 7: Generate forecast including historical period for visualization
    future = final_model.make_future_dataframe(periods=30)
    full_forecast = final_model.predict(future)
    
    # Step 8: Create visualization
    print(f"\nGenerating visualization...")
    plot_file = plot_forecast_vs_actual(location, train_df, test_df, full_forecast, output_dir)
    
    # Step 9: Extract and save future forecast
    future_forecast = full_forecast.tail(30)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    future_forecast.columns = ['date', 'forecast', 'lower_bound', 'upper_bound']
    
    # Ensure non-negative forecasts (packages can't be negative)
    for col in ['forecast', 'lower_bound', 'upper_bound']:
        future_forecast[col] = future_forecast[col].clip(lower=0)
    
    # Step 10: Save artifacts
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    model_file = output_path / f'location_{location}_model.pkl'
    with open(model_file, 'wb') as f:
        pickle.dump(final_model, f)
    
    forecast_file = output_path / f'location_{location}_forecast.csv'
    future_forecast.to_csv(forecast_file, index=False)
    
    # Step 11: Save metadata and metrics
    results = {
        'location': location,
        'metadata': metadata,
        'cv_metrics': {
            'avg_rmse': cv_results['avg_rmse'],
            'avg_mae': cv_results['avg_mae'],
            'avg_wape': cv_results['avg_wape'],
            'avg_interval_coverage': cv_results['avg_interval_coverage'],
            'avg_interval_width': cv_results['avg_interval_width'],
            'std_rmse': cv_results['std_rmse'],
            'std_mae': cv_results['std_mae'],
            'std_wape': cv_results['std_wape'],
            'std_interval_coverage': cv_results['std_interval_coverage'],
            'std_interval_width': cv_results['std_interval_width'],
            'n_folds': cv_results['n_folds']
        },
        'baseline_cv_metrics': {
            'avg_rmse': cv_results['baseline_avg_rmse'],
            'avg_mae': cv_results['baseline_avg_mae'],
            'avg_wape': cv_results['baseline_avg_wape'],
            'avg_interval_coverage': cv_results['baseline_avg_interval_coverage'],
            'avg_interval_width': cv_results['baseline_avg_interval_width'],
            'std_rmse': cv_results['baseline_std_rmse'],
            'std_mae': cv_results['baseline_std_mae'],
            'std_wape': cv_results['baseline_std_wape'],
            'std_interval_coverage': cv_results['baseline_std_interval_coverage'],
            'std_interval_width': cv_results['baseline_std_interval_width'],
            'n_folds': cv_results['n_folds']
        },
        'test_metrics': test_metrics,
        'baseline_test_metrics': baseline_test_metrics,
        'forecast_file': str(forecast_file),
        'model_file': str(model_file),
        'splits_file': splits_file,
        'plot_file': plot_file
    }
    
    results_file = output_path / f'location_{location}_results.json'
    with open(results_file, 'w') as f:
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
                       output_dir: str = 'models',
                       locations: list = None) -> Dict:
    """
    Train models for all specified locations.
    
    Args:
        data_path: Path to the raw CSV data
        output_dir: Directory to save trained models and forecasts
        locations: List of location identifiers (default: ['A', 'B', 'C'])
        
    Returns:
        Dictionary with results for all locations
    """
    if locations is None:
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
    results = train_all_locations()
